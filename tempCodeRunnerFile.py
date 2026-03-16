
from fastapi import FastAPI, Depends, Request, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.dependency import get_db
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text, create_engine
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from geopy.geocoders import Nominatim
import time

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def hash_pass(password: str) -> str:
    return pwd_context.hash(password)
def verify_pass(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

@app.get("/status")
async def root():
    return {"status": "ok"}

@app.get("/items/")
async def read_items(db: AsyncSession = Depends(get_db)):
    # Example query: result = await db.execute(select(Item))
    # items = result.scalars().all()
    return {"message": "Database connected successfully"}

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse(
        "Home.html",
        {"request": request, "name": "User"}
    )

@app.get("/db-test")
async def db_test(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT 1"))
    return {"db_ok": True, "value": result.scalar_one()}

@app.get("/user_dashboard", response_class=HTMLResponse)
def user_dashboard(request: Request):
    return templates.TemplateResponse("UserDashboard.html", {"request": request})

@app.get("/venue_dashboard", response_class=HTMLResponse)
def user_dashboard(request: Request):
    return templates.TemplateResponse("VenueDashboard.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    email = email.strip().lower()

    result = await db.execute(
        text("SELECT 1 FROM users WHERE Email = :email LIMIT 1"),
        {"email": email}
    )
    existing_user = result.first()
    if existing_user:
        return templates.TemplateResponse(
        "register.html",
        {"request": request, "error": "Email already registered"},
        status_code=409,
    )

    hashed = hash_pass(password)

    try:
        await db.execute(
            text("""
                INSERT INTO users (Email, Password, Role, Status)
                VALUES (:email, :password, :role, 'Active')
            """),
            {"email": email, "password": hashed, "role": role},
        )
        await db.commit()

    except Exception as e:
        await db.rollback()
        print("ERROR TYPE:", type(e))
        print("ERROR MESSAGE:", repr(e))
        raise

    return RedirectResponse(url="/user_dashboard", status_code=303)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    email = email.strip().lower()

    result = await db.execute(
        text("""
            SELECT UserID, Email, Password, Role, Status
            FROM users
            WHERE Email = :email
            LIMIT 1
        """),
        {"email": email},
    )
    user = result.mappings().first()

    if not user or not verify_pass(password, user["Password"]):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password", "email": email},
            status_code=401,
        )

    if user["Status"] != "Active":
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "User is not active", "email": email},
            status_code=403,
        )
    if user["Role"] == "User":
        return RedirectResponse(url="/user_dashboard", status_code=303)
    if user["Role"] == "Venue":
        return RedirectResponse(url="/venue_dashboard", status_code=303)
    

engine = create_engine("sqlite+aiosqlite:///./app.db", future=True)
geolocator = Nominatim(user_agent="eventhub_app") 

@app.get("/api/events")
async def get_events(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("""
        SELECT
            e.EventID,
            e.Name AS EventName,
            v.VenueName AS VenueName,
            v.Location
        FROM Events e
        JOIN Venues v ON v.VenueID = e.VenueID
        WHERE e.Approved = 1
    """))
    rows = result.mappings().all()

    return [
        {
            "EventID": r["EventID"],
            "EventName": r["EventName"],
            "VenueName": r["VenueName"],
            "Location": r["Location"]
        }
        for r in rows
    ]

@app.get("/events", response_class=HTMLResponse)
async def events_page(
    request: Request,
    category: int | None = None,
    db: AsyncSession = Depends(get_db)
):

    query = """
        SELECT
            e.EventID,
            e.Name,
            e.StartDate,
            e.EndDate,
            e.TicketPrice,
            e.ImageURL,
            v.VenueName,
            v.Location,
            c.Name as Category
        FROM Events e
        JOIN Venues v ON v.VenueID = e.VenueID
        JOIN Category c ON c.CategoryID = e.CategoryID
        WHERE e.Approved = 1
    """

    params = {}

    if category:
        query += " AND e.CategoryID = :category"
        params["category"] = category

    result = await db.execute(text(query), params)
    events = result.mappings().all()

    cat_result = await db.execute(text("SELECT * FROM Category"))
    categories = cat_result.mappings().all()

    return templates.TemplateResponse(
        "EventDetails.html",
        {
            "request": request,
            "events": events,
            "categories": categories
        }
    )