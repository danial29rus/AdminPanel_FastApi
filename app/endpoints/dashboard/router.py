from fastapi import Depends, Request, Response, HTTPException, APIRouter, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, insert, delete, inspect, update, Table
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import class_mapper, declarative_base
from starlette.responses import RedirectResponse, PlainTextResponse

from app.database import get_async_session, Base
from app.endpoints.auth.models import Users
from app.endpoints.dashboard.models import Item

router_dashboard = APIRouter()
templates = Jinja2Templates(directory="templates")


@router_dashboard.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_async_session)):
    user_count = await db.execute(select(func.count(Users.id)))
    user_count = user_count.scalar_one()

    item_count = await db.execute(select(func.count(Item.id)))
    item_count = item_count.scalar_one()

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user_count": user_count, "item_count": item_count},
    )


@router_dashboard.get("/model/{model_name}")
async def model_handler(request: Request, model_name: str, db: AsyncSession = Depends(get_async_session)):
    model = Base.metadata.tables[model_name]
    fields = [field.name for field in model.columns]
    rows = await db.execute(select(model))
    rows = rows.fetchall()
    return templates.TemplateResponse(
        "model.html",
        {"request": request, "model_name": model_name, "fields": fields, "rows": rows, "getattr": getattr},
    )


@router_dashboard.get("/model/{model_name}/create")
async def new_handler(request: Request, model_name: str):
    model = Base.metadata.tables[model_name]
    fields = [field.name for field in model.columns]
    return templates.TemplateResponse('create.html', {'request': request, 'model_name': model_name, 'fields': fields})




@router_dashboard.post("/model/{model_name}/create")
async def do_create_handler(request: Request, model_name: str, db: AsyncSession = Depends(get_async_session)):
    table = Base.metadata.tables[model_name]
    class_name = table.name.capitalize()
    model_class = type(class_name, (Base,), {'__tablename__': table.name, '__table__': table})

    form_data = await request.form()
    form_data = {k: int(v) if k == 'user_id' else v for k, v in form_data.items()}  # преобразование user_id в int
    instance = model_class(**form_data)

    db.add(instance)
    try:
        await db.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create instance: {e}")

    return templates.TemplateResponse("dashboard.html", {"request": request})




@router_dashboard.post("/model/{model_name}/delete/{id}")
async def do_delete_handler(request: Request, model_name: str, id: int, db: AsyncSession = Depends(get_async_session)):
    model = Base.metadata.tables[model_name]

    if model_name == "users":
        # Если удаляем пользователя, нужно сначала удалить все связанные записи в таблице `items`
        # Удаляем все связанные записи в таблице items
        items_model = Base.metadata.tables["Item"]
        stmt = delete(items_model).where(items_model.c.user_id == id)
        await db.execute(stmt)

    # Удаляем пользователя или запись из другой таблицы
    stmt = delete(model).where(model.c.id == id)
    await db.execute(stmt)

    await db.commit()
    return RedirectResponse(f"/model/{model_name}")


@router_dashboard.get("/model/{model_name}/edit/{id}")
async def edit_handler(request: Request, model_name: str, id: int, db: AsyncSession = Depends(get_async_session)):
    model = Base.metadata.tables[model_name]
    fields = [field.name for field in model.columns]
    row = await db.execute(select(model).where(model.c.id == id))
    row = row.fetchone()

    return templates.TemplateResponse(
        "edit.html",
        {"request": request, "model_name": model_name, "fields": fields, "row": row, "id": id},
    )


@router_dashboard.post("/model/{model_name}/edit/{id}")
async def do_edit_handler(request: Request, model_name: str, id: int, db: AsyncSession = Depends(get_async_session)):
    model = Base.metadata.tables[model_name]
    form_data = await request.form()
    update_stmt = (
        update(model)
        .where(model.c.id == id)
        .values(**{ k: int(v) if k in ['user_id', 'id'] else v for k, v in form_data.items() })
    )

    try:
        await db.execute(update_stmt)
        await db.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update instance: {e}")

    return RedirectResponse(f"/model/{model_name}")



