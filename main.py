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
from fastapi import UploadFile, File

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

@app.get("/")
def home(request: Request):
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            ev.VariantID,
            e.EventID,
            e.Name,
            e.StartDate,
            e.ImageURL,
            v.VenueName
        FROM Events e
        JOIN EventVariants ev ON e.EventID = ev.EventID
        LEFT JOIN Venues v ON ev.VenueID = v.VenueID
        WHERE ev.Approved = 1
        GROUP BY ev.VariantID
        ORDER BY RANDOM()
        LIMIT 6
    """)

    featured_events = cur.fetchall()

    return templates.TemplateResponse("Home.html", {
        "request": request,
        "featured_events": featured_events
    })

@app.get("/db-test")
async def db_test(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT 1"))
    return {"db_ok": True, "value": result.scalar_one()}

@app.get("/user_dashboard", response_class=HTMLResponse)
def user_dashboard(request: Request):
    return templates.TemplateResponse("UserDashboard.html", {"request": request})

@app.get("/venue_dashboard", response_class=HTMLResponse)
async def venue_dashboard(request: Request,  db: AsyncSession = Depends(get_db)):
    try:
        venues_result = await db.execute(text("""
            SELECT VenueID, VenueName, Location, Reviews, SeatingCapacity 
            FROM Venues
        """))
        venues = venues_result.mappings().all()

        result = await db.execute(text("""
            SELECT SlotID, TimeStart, TimeEnd 
            FROM TimeSlots
        """))
        time_slots = result.mappings().all()

        savedVenueId = request.session.get("venue_id")
        
        return templates.TemplateResponse("VenueDashboard.html", {
            "request": request,
            "venues": venues,
            "time_slots": time_slots,
            "savedVenueId": savedVenueId
        })

    except Exception as e:
        print("ERROR:", e)
        raise

@app.post("/save_venue_choice")
async def save_venue_choice(request: Request, VenueID: int = Form(...)):
    request.session["venue_id"] = VenueID
    return RedirectResponse("/venue_dashboard", status_code=303)

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    name: str = Form(...),
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
                INSERT INTO Users (Name, Email, Password, Role, Status)
                VALUES (:name, :email, :password, :role, 'Active')
            """),
            {"name": name, "email": email, "password": hashed, "role": role},
        )
        await db.commit()

    except Exception as e:
        await db.rollback()
        print("ERROR TYPE:", type(e))
        print("ERROR MESSAGE:", repr(e))
        raise

    if role == "seeker":
        return RedirectResponse(url="/user_dashboard", status_code=303)
    if role == "host":
        return RedirectResponse(url="/venue_dashboard", status_code=303)
    if role == "admin":
        return RedirectResponse(url="/admin_view", status_code=303)

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
            FROM Users
            WHERE Email = :email
            LIMIT 1
        """),
        {"email": email},
    )
    user = result.mappings().first()


    if user:
        print("USER KEYS:", user.keys())
    else:
        print("USER NOT FOUND")


    if not user or not verify_pass(password, user["Password"]):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password", "email": email},
            status_code=401,
        )
    
    request.session["user"] = {
        "Status": user["Status"]
    }

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

    if user["Role"] == "seeker":
        return RedirectResponse(url="/user_dashboard", status_code=303)
    if user["Role"] == "host":
        return RedirectResponse(url="/venue_dashboard", status_code=303)
    if user["Role"] == "admin":
        return RedirectResponse(url="/admin_view", status_code=303)
    

engine = create_engine("sqlite+aiosqlite:///./app.db", future=True)
geolocator = Nominatim(user_agent="eventhub_app") 

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return templates.TemplateResponse("Home.html", {"request": request})

@app.get("/events")
def browse_events(request: Request, category: int = None):
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = """
        SELECT 
            ev.VariantID,
            e.EventID,
            e.Name,
            e.ImageURL,
            e.StartDate,
            c.Name AS Category,
            v.VenueName,
            v.Location,
            ev.TicketPrice
        FROM EventVariants ev
        JOIN Events e ON ev.EventID = e.EventID
        LEFT JOIN Venues v ON ev.VenueID = v.VenueID
        JOIN Category c ON e.CategoryID = c.CategoryID
        WHERE ev.Publicity = 0
        AND ev.Approved = 1
    """

    params = []

    if category:
        query += " AND e.CategoryID = ?"
        params.append(category)

    query += " ORDER BY e.StartDate ASC"

    cur.execute(query, params)
    events = cur.fetchall()

    cur.execute("SELECT * FROM Category")
    categories = cur.fetchall()

    return templates.TemplateResponse("EventDetails.html", {
        "request": request,
        "events": events,
        "categories": categories
    })

@app.get("/api/events")
def get_events():
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT
            e.EventID,
            e.Name AS EventName,
            e.ImageURL,
            v.VenueName,
            v.Location,
            v.Latitude,
            v.Longitude
        FROM Events e
        JOIN EventVariants ev ON e.EventID = ev.EventID
        JOIN Venues v ON ev.VenueID = v.VenueID
        WHERE ev.Approved = 1
        AND v.Latitude IS NOT NULL
        AND v.Longitude IS NOT NULL
        AND e.StartDate <= CURRENT_DATE
        AND e.EndDate >= CURRENT_DATE
    """)

    rows = cur.fetchall()
    conn.close()

    return [dict(row) for row in rows]

@app.get("/events/view/{variant_id}")
def event_view(request: Request, variant_id: int):
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            ev.VariantID,
            e.Name,
            e.Description,
            e.ImageURL,
            e.StartDate,
            c.Name AS Category,
            v.VenueName,
            v.Location,
            ev.TicketPrice,
            ts.TimeStart,
            ts.TimeEnd
        FROM EventVariants ev
        JOIN Events e ON ev.EventID = e.EventID
        LEFT JOIN Venues v ON ev.VenueID = v.VenueID
        JOIN Category c ON e.CategoryID = c.CategoryID
        JOIN TimeSlots ts ON ev.SlotID = ts.SlotID
        WHERE ev.VariantID = ?
    """, (variant_id,))

    event = cur.fetchone()

    return templates.TemplateResponse("EventView.html", {
        "request": request,
        "event": event
    })

@app.post("/create_event")
async def create_event(
    request: Request,
    name: str = Form(...),
    start: str = Form(None),
    end: str = Form(None),
    slot_id: int = Form(...),
    category_id: int = Form(...),
    desc: str = Form(...),
    poster: UploadFile = Form(None),
    price: int = Form(0),
    db: AsyncSession = Depends(get_db),
):
    try:
        venue_id = request.session.get("venue_id")

        if not venue_id:
           return {"error": "Please select a venue first"}
        print("SESSION:", request.session)
        user = request.session.get("user")
        if not user:
            return RedirectResponse("/login", status_code=303)
        
        file_path = None

        if poster:
            upload_dir = "static/uploads"
            os.makedirs(upload_dir, exist_ok=True)

            file_path = f"{upload_dir}/{poster.filename}"

            with open(file_path, "wb") as f:
                content = await poster.read()
                f.write(content)

        result = await db.execute(text("""
            INSERT INTO Events (
                CategoryID, Name, 
                StartDate, EndDate, Description,
                ImageURL
            )
            VALUES (
                :category_id, :name, 
                :start, :end, :desc,
                :image_url
            )
            RETURNING EventID
        """), {
            "category_id": category_id,
            "name": name,
            "start": start,
            "end": end,
            "desc": desc,
            "image_url": file_path,
        })

        event_id = result.scalar()

        await db.execute(text("""
            INSERT INTO EventVariants (
                HostID, Publicity, Approved, VenueID, EventID, TicketPrice, SlotID
            )
            VALUES (
                :host_id, :publicity, :approved, :venue_id, :event_id, :price, :slot_id
            )
        """), {
            "host_id": user["UserID"],
            "publicity": 1,
            "venue_id": venue_id,
            "approved": False,
            "slot_id": slot_id,
            "event_id": event_id,
            "price": price,
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
            "Location": full_address,
            "Longitude": f"{geo.longitude}",
            "Latitude": f"{geo.latitude}",

        })      

        venue_id = result.scalar()
        await db.commit()

        request.session["VenueId"] = venue_id

    except Exception as e:
        return {"error": str(e)}

    return RedirectResponse("/venue_dashboard", status_code=303)

@app.get("/admin_view", response_class=HTMLResponse)
def admin_view(request: Request):
    user = request.session.get("user")

    if not user or user.get("Role") != "admin":
        return RedirectResponse("/login", status_code=303)

    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Venues")
    venues = cursor.fetchall()

    conn.close()

    return templates.TemplateResponse(
        "AdminView.html",
        {
            "request": request,
            "venues": venues
        }
    )

@app.post("/admin/add-venue")
async def add_venue(
    request: Request,
    venue_name: str = Form(...),
    street: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    zip: str = Form(...),
    seating_capacity: int = Form(None),
    reviews: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    user = request.session.get("user")

    if not user:
        return RedirectResponse("/login", status_code=303)

    owner_id = user["UserID"]

    full_address = f"{street}, {city}, {state} {zip}"

    geo = geolocator.geocode(full_address, timeout=10)
    if not geo:
        return {"error": "Invalid address"}
    
    lat = geo.latitude
    lng = geo.longitude

    result = await db.execute(text("""
            INSERT INTO Venues 
            (VenueName, Location, Latitude, Longitude, SeatingCapacity, Reviews, OwnerID)
            VALUES (:name, :location, :lat, :lng, :capacity, :reviews, :owner)
            RETURNING VenueID
        """), {
            "name": venue_name,
            "location": full_address,
            "lat": lat,
            "lng": lng,
            "capacity": seating_capacity,
            "reviews": reviews,
            "owner": user["UserID"]
        })  
    
    await db.commit()

    return RedirectResponse("/admin_view", status_code=303)