from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from pydantic import BaseModel, EmailStr

from datetime import datetime, timedelta, timezone
import jwt

from database import get_async_session
from config import settings
from models import User, Admin, Account, Payment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import hashlib
from decimal import Decimal


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = None


class WebhookData(BaseModel):
    transaction_id : str
    account_id: int
    amount: Decimal
    signature: str


app = FastAPI(title="Payment Service")


def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=30)) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})

    encode_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encode_jwt


@app.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_async_session)):
    user_query = await session.execute(select(User).where(User.email == form_data.username))
    user = user_query.scalar_one_or_none()

    if user and user.hashed_password == form_data.password:
        token = create_access_token(data={"sub": str(user.id), "role": "user"})
        return {"access_token": token, "token_type": "bearer"}
    
    admin_query = await session.execute(select(Admin).where(Admin.email == form_data.username))
    admin = admin_query.scalar_one_or_none()

    if admin and admin.hashed_password == form_data.password:
        token = create_access_token(data={"sub": str(admin.id), "role": "admin"})
        return {"access_token": token, "token_type": "bearer"}
    
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или password")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")

        if role != "user":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступно только для пользователей")
        return {"user_id": int(user_id), "role": role}
    except jwt.PyJWKError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный или просроченный токен")


async def get_current_admin(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        admin_id: str = payload.get("sub")
        role: str = payload.get("role")

        if role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступно только для администраторов")
        return {"admin_id": int(admin_id), "role": role}
    except jwt.PyJWKError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный или просроченный токен")
    
@app.get("/user/me")
async def get_me(current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    query = await session.execute(select(User).where(User.id == current_user["user_id"]))
    user = query.scalar_one_or_none()
    
    return {"id": user.id, "email": user.email, "full_name": user.full_name}


@app.get("/user/accounts")
async def get_my_accounts(current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    query = await session.execute(select(Account).where(Account.id == current_user["user_id"]))
    accounts = query.scalars().all()

    return [{"id": acc.id, "balance": acc.balance} for acc in accounts]


@app.get("/user/payments")
async def get_my_payments(current_user: dict = Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    query = await session.execute(select(Payment).where(Payment.user_id == current_user["user_id"]))
    payments = query.scalars().all()
    
    return [{"id": p.id, "account_id": p.account_id, "transaction_id": p.transaction_id, "amount": p.amount} for p in payments]

@app.get("/admin/me")
async def get_me(current_admin: dict = Depends(get_current_admin), session: AsyncSession = Depends(get_async_session)):
    query = await session.execute(select(Admin).where(Admin.id == current_admin["admin_id"]))
    admin = query.scalar_one_or_none()
    
    return {"id": admin.id, "email": admin.email, "full_name": admin.full_name}


@app.get("/admin/users")
async def get_all_users(current_admin: dict = Depends(get_current_admin), session: AsyncSession = Depends(get_async_session)):
    query = await session.execute(select(User))
    users = query.scalars().all()

    result = []
    for user in users:
        acc_query = await session.execute(select(Account).where(Account.user_id == user.id))
        accounts = acc_query.scalars().all()

        result.append({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "accounts": [{"id": acc.id, "balance": acc.balance} for acc in accounts]
        })

    return result

@app.post("/admin/users")
async def create_user(body: UserCreate, current_admin: dict = Depends(get_current_admin), session: AsyncSession = Depends(get_async_session)):
    check_query = await session.execute(select(User).where(User.email == body.email))
    if check_query.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
    
    new_user = User(email = body.email, hashed_password=body.password, full_name=body.full_name)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return {"status": "success", "user_id": new_user.id}

@app.put("/admin/users/{user_id}")
async def update_user(user_id: int, body: UserUpdate, current_admin: dict = Depends(get_current_admin), session: AsyncSession = Depends(get_async_session)):
    query = await session.execute(select(User).where(User.id == user_id))
    user = query.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    if body.email:
        user.email = body.email
    if body.full_name:
        user.full_name = body.full_name
    if body.password:
        user.hashed_password = body.password

    await session.commit()

    return {"status": "updated"}

@app.delete("/admin/users/{user_id}")
async def update_user(user_id: int, current_admin: dict = Depends(get_current_admin), session: AsyncSession = Depends(get_async_session)):
    query = await session.execute(select(User).where(User.id == user_id))
    user = query.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    await session.delete(user)
    await session.commit()

    return {"status": "deleted"}


@app.post("/webhook/payment")
async def handle_payment_webhook(body: WebhookData, session: AsyncSession = Depends(get_async_session)):
    data_to_sign = f"{body.transaction_id}:{body.account_id}:{body.amount}:{settings.SECRET_KEY}"
    print("\n" + "="*40 + f"\nСТРОКА НА БЭКЕНДЕ: {data_to_sign}\n" + "="*40 + "\n")
    my_signature = hashlib.sha256(data_to_sign.encode('utf-8')).hexdigest()
    print(my_signature)

    if my_signature != body.signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверная цифровая подпись! Доступ заблокирован")
    
    acc_query = await session.execute(select(Account).where(Account.id == body.account_id))
    account = acc_query.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Счёт не найден")
    
    payment_query = await session.execute(select(Payment).where(Payment.transaction_id == body.transaction_id))
    if payment_query.scalar_one_or_none():
        return {"status": "already_processed", "detail": "Этот платеж был зачислен"}

    account.balance += body.amount

    new_payment = Payment(
        transaction_id = body.transaction_id,
        user_id = account.user_id,
        account_id = account.id,
        amount=body.amount
    )

    session.add(new_payment)
    await session.commit()

    return {"status": "success", "msg": f"Баланс был пополнен на: {body.amount}"}



