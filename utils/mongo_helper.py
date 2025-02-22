# utils/mongo_helper.py
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import streamlit as st
import bcrypt
from datetime import datetime, timezone
import json


@st.cache_resource
def init_connection():
    """Initialize MongoDB connection using cached resource"""
    try:
        # Get credentials from secrets
        username = st.secrets['username']
        password = st.secrets['password']

        # Simple connection string
        uri = (
            "mongodb+srv://"
            f"{username}:{password}@"
            "cluster0.wbd1o.mongodb.net/"
            "?retryWrites=true&w=majority"
        )

        # Create client with minimal configuration
        client = MongoClient(
            uri,
            server_api=ServerApi('1')
        )

        # Test connection
        client.admin.command('ping')
        print("✅ Connected to MongoDB")
        return client

    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        st.error(f"Database connection failed")
        return None


def get_collection(database_name: str, collection_name: str):
    client = init_connection()
    if client is None:  # Explicitly check for None
        return None
    return client[database_name][collection_name]


def hash_password(password: str) -> tuple:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed, salt


def verify_password(password: str, hashed_password: bytes) -> bool:
    """Verify password against hashed version"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)


def create_user(username: str, password: str, user_data: dict = None) -> tuple[bool, str]:
    """Create new user with hashed password"""
    collection = get_collection("fitlistic", "users")
    if collection is None:  # Explicitly check for None
        return False, "Database connection failed"

    try:
        # Check if username exists
        existing_user = collection.find_one({"username": username.lower()})
        if existing_user is not None:  # Explicitly check for None
            return False, "Username already exists. Please choose another one"

        # Check if email exists
        if user_data and 'email' in user_data:
            existing_email = collection.find_one({"email": user_data['email'].lower()})
            if existing_email is not None:  # Explicitly check for None
                return False, "Email already registered"

        # Hash password
        hashed_pw, salt = hash_password(password)

        # Prepare user document
        user_document = {
            "username": username.lower(),
            "password": hashed_pw,
            "salt": salt,
            "created_at": datetime.now(timezone.utc),
            "last_login": datetime.now(timezone.utc),
            "total_workouts": 0,
            "workout_history": []
        }

        if user_data:
            if 'email' in user_data:
                user_data['email'] = user_data['email'].lower()
            user_document.update(user_data)

        # Insert user
        result = collection.insert_one(user_document)
        if result.inserted_id:
            return True, "User created successfully"
        return False, "Failed to create user"

    except Exception as e:
        return False, str(e)


def validate_login(username: str, password: str) -> tuple[bool, dict | None]:
    """Validate user login credentials"""
    collection = get_collection("fitlistic", "users")
    if collection is None:  # Explicitly check for None
        return False, None

    try:
        user = collection.find_one({"username": username.lower()})
        if user is not None and verify_password(password, user["password"]):  # Explicitly check for None
            # Update last login time
            collection.update_one(
                {"username": username.lower()},
                {"$set": {"last_login": datetime.now(timezone.utc)}}
            )
            return True, user
        return False, None
    except Exception:
        return False, None


# Additional functions for fitness plan management
def save_user_plan(user_id: str, plan_data: dict):
    """Save a user's workout plan"""
    collection = get_collection("fitlistic", "user_plans")
    if collection is None:
        return False, "Database connection failed"

    try:
        # Deactivate old plans
        collection.update_many(
            {"user_id": user_id, "is_active": True},
            {"$set": {"is_active": False}}
        )

        # Create new plan document
        plan_document = {
            "user_id": user_id,
            "plan_data": plan_data,
            "created_at": datetime.now(timezone.utc),
            "is_active": True,
            "completion_status": {day: False for day in plan_data['schedule'].keys()}
        }

        result = collection.insert_one(plan_document)
        return True, str(result.inserted_id)

    except Exception as e:
        return False, str(e)


def get_active_plan(user_id: str):
    """Get user's active workout plan"""
    collection = get_collection("fitlistic", "user_plans")
    if collection is None:
        return None

    try:
        return collection.find_one({
            "user_id": user_id,
            "is_active": True
        })
    except Exception:
        return None


def initialize_fitness_collections():
    """Initialize fitness-related collections with sample data"""
    client = init_connection()
    if client is None:
        return False

    db = client['fitlistic']

    try:
        # Initialize collections if empty
        collections_data = {
            'exercises': 'exercises.json',
            'breathwork_techniques': 'breathwork_techniques.json',
            'meditation_templates': 'meditation_templates.json',
            'stretching_routines': 'stretching_routines.json'
        }

        for coll_name, filename in collections_data.items():
            if db[coll_name].count_documents({}) == 0:
                try:
                    with open(f'data/{filename}', 'r') as f:
                        data = json.load(f)
                        db[coll_name].insert_many(data)
                        print(f"✅ Initialized {coll_name} collection")
                except FileNotFoundError:
                    print(f"❌ File not found: data/{filename}")
                except Exception as e:
                    print(f"❌ Error loading {filename}: {str(e)}")

        return True

    except Exception as e:
        print(f"Error initializing collections: {str(e)}")
        return False
