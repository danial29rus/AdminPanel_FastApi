from datetime import timedelta

from fastapi import Depends, APIRouter, Form
from fastapi import status, HTTPException
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import Response, HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates

from app.endpoints.auth.manager import authenticate_user, Token, ACCESS_TOKEN_EXPIRE_MINUTES, \
    create_access_token, PasswordRequestForm, get_password_hash
from app.endpoints.auth.models import Users
from app.endpoints.auth.schemas import User
from app.endpoints.auth.utils import get_current_user
from app.database import get_async_session

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register", status_code=201)
async def register_user(
        form_data: PasswordRequestForm = Depends(),
        session: AsyncSession = Depends(get_async_session),
):
    hashed_password = get_password_hash(form_data.password)
    check_existing_email = select(Users).filter_by(email=form_data.email)
    existing_user = await session.execute(check_existing_email)
    if existing_user.scalar():  # если пользователь существует, вернуть ошибку
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с такой почтой уже существует",
        )
    stmt = insert(Users).values(
        email=form_data.email,
        hashed_password=hashed_password
    )
    await session.execute(stmt)
    await session.commit()

    return templates.TemplateResponse(
        "register.html",
        {"request": form_data}
    )


@router.post("/login", response_model=Token)
async def login_user(
        response: Response,
        form_data: PasswordRequestForm = Depends(),
):
    user = await authenticate_user(form_data.email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    response.set_cookie("booking_access_token", access_token)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout_user(response: Response):
    response.delete_cookie("booking_access_token")
    return None


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.route("/login", methods=["GET", "POST"])
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    if request.method == "POST":
        form_data = PasswordRequestForm(email=email, password=password)
        token = await login_user(response=Response(), form_data=form_data)
        response = RedirectResponse(url="/dashboard")
        response.set_cookie(key="access_token", value=token.access_token)
        return response
    return templates.TemplateResponse("login.html", {"request": request})
