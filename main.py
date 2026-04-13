from fastapi import FastAPI, Depends, Request, Form, HTTPException, status, UploadFile, File
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
import sqlite3
from starlette.middleware.sessions import SessionMiddleware
import os, shutil, uuid

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")
# from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key="skeletonkey")

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

from fastapi import Request
from fastapi.responses import HTMLResponse
import sqlite3

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            Events.EventID,
            Events.Name,
            Events.StartDate,
            Events.ImageURL,
            Venues.VenueName AS VenueName,
            Venues.Location AS VenueLocation
        FROM Events
        JOIN Venues ON Events.VenueID = Venues.VenueID
        WHERE Events.Approved = 1
          AND Events.PublicityLevel = 'Public'
        ORDER BY date(Events.StartDate) ASC
        LIMIT 3
    """)

    featured_events = cursor.fetchall()
    conn.close()

    return templates.TemplateResponse(
        "Home.html",
        {
            "request": request,
            "name": "User",
            "featured_events": featured_events
        }
    )

@app.get("/db-test")
async def db_test(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT 1"))
    return {"db_ok": True, "value": result.scalar_one()}

@app.get("/user_dashboard", response_class=HTMLResponse)
def user_dashboard(request: Request):
    return templates.TemplateResponse("UserDashboard.html", {"request": request})

@app.get("/venue_dashboard", response_class=HTMLResponse)
async def venue_dashboard(request: Request,  db: AsyncSession = Depends(get_db)):
    venue_id = request.session.get("VenueId")
    has_venue = bool(venue_id)

    venue_name = None

    if venue_id:
        result = await db.execute(text("""
            SELECT VenueName FROM Venues WHERE VenueID = :id
        """), {"id": venue_id})

        venue_name = result.scalar()
        result = await db.execute(text("""
            SELECT TimeID, StartTime, EndTime 
            FROM TimeSlots
        """))
        time_slots = result.mappings().all()
        return templates.TemplateResponse("VenueDashboard.html", {
            "request": request,
            "has_venue": has_venue,
            "venue_name": venue_name,
            "time_slots": time_slots
        })

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    type: str = Form(...),
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

    if type == "User":
        return RedirectResponse(url="/user_dashboard", status_code=303)
    if type == "Venue":
        return RedirectResponse(url="/venue_dashboard", status_code=303)

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
    request.session["user"] = {
        "UserID": user["UserID"],
        "Role": user["Role"]
    }
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
            v.Location,
            e.ImageURL
        FROM Events e
        JOIN Venues v ON v.VenueID = e.VenueID
        
    """))
    # WHERE e.Approved = 1

    rows = result.mappings().all()
    events = []

    for r in rows:
        lat, lng = None, None

        if r["Location"] and "," in r["Location"]:
            try:
                lat, lng = map(float, r["Location"].split(","))
            except Exception as e:
                print("BAD LOCATION:", r["Location"], e)

        events.append({
            "EventID": r["EventID"],
            "EventName": r["EventName"],
            "VenueName": r["VenueName"],
            "Location": r["Location"],
            "ImageURL": r["ImageURL"],
            "Latitude": lat,
            "Longitude": lng
        })

    return events

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

@app.post("/create_event")
async def create_event(
    request: Request,
    name: str = Form(...),
    start: str = Form(None),
    end: str = Form(None), 
    time_id: int = Form(...),
    category_id: int = Form(...),
    desc: str = Form(...),
    venue_name: str = Form(None),
    street: str = Form(None),
    city: str = Form(None),
    state: str = Form(None),
    zip: str = Form(None),
    price: float = Form(...),
    poster: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        print("SESSION:", request.session)
        user = request.session.get("user")
        if not user:
            return RedirectResponse("/login", status_code=303)
        
        venue_id = request.session.get("VenueId")

        if venue_name and city and state:
    
            full_address = f"{street}, {city}, {state} {zip}"

            print("ADDRESS:", full_address)

            geo = geolocator.geocode(full_address)

            print("GEO RESULT:", geo)

            if not geo:
                return {"error": "Invalid address"}
            
            location = f"{geo.latitude},{geo.longitude}"

            result = await db.execute(text("""
                INSERT INTO venues (VenueName, Location)
                VALUES (:name, :location)
                RETURNING VenueID
            """), {
                "name": venue_name,
                "location": location
            })

            venue_id = result.scalar()
            await db.commit()

            request.session["VenueId"] = venue_id

        if not venue_id:
            return {"error": "Please enter a venue"}

        await db.execute(text("""
            INSERT INTO events (
                VenueID, CategoryID, TimeID,
                Name, Description,
                StartDate, EndDate,
                TicketPrice, Approved
            )
            VALUES (
                :venue_id, :category_id, :time_id,
                :name, :desc,
                :start, :end,
                :price, 0
            )
        """), {
            "venue_id": venue_id,
            "category_id": category_id,
            "time_id": time_id,
            "name": name,
            "desc": desc,
            "start": start,
            "end": end,
            "price": price
        })

        await db.commit()

    except Exception as e:
        return {"error": str(e)}

    return RedirectResponse("/venue_dashboard", status_code=303)

@app.post("/save_venue")
async def save_venue(
    request: Request,
    venue_name: str = Form(...),
    street: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    zip: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = request.session.get("user")
        if not user:
            return RedirectResponse("/login", status_code=303)

        full_address = f"{street}, {city}, {state} {zip}"

        geo = geolocator.geocode(full_address, timeout=10)

        if not geo:
            return {"error": "Invalid address"}

        location = f"{geo.latitude},{geo.longitude}"

        result = await db.execute(text("""
            INSERT INTO Venues (VenueName, Location)
            VALUES (:name, :location)
            RETURNING VenueID
        """), {
            "name": venue_name,
            "location": location
        })

        venue_id = result.scalar()
        await db.commit()

        request.session["VenueId"] = venue_id

    except Exception as e:
        return {"error": str(e)}

    return RedirectResponse("/venue_dashboard", status_code=303)