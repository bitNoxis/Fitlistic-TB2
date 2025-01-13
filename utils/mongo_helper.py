import streamlit as st
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import bcrypt
from datetime import datetime, timezone


@st.cache_resource
def init_connection():
    """Initialize MongoDB connection using cached resource"""
    username = st.secrets['username']
    password = st.secrets['password']

    try:
        client = MongoClient(
            f"mongodb+srv://{username}:{password}@cluster0.wbd1o.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
            server_api=ServerApi('1')
        )
        # Verify connection with clear ping message
        client.admin.command('ping')
        print("✅ MongoDB Connection successful! Database is ready.")
        return client
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        st.error(f"Database connection failed: {str(e)}")
        return None


def get_collection(database_name: str, collection_name: str):
    """Get MongoDB collection with error handling"""
    client = init_connection()
    if client:
        return client[database_name][collection_name]
    return None


def hash_password(password: str) -> tuple:
    """Hash password using bcrypt with salt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed, salt


def verify_password(password: str, hashed_password: bytes) -> bool:
    """Verify password against hashed version"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)


class UserManager:
    def __init__(self):
        self.collection = get_collection("fitlistic", "users")

    def create_user(self, username: str, password: str, user_data: dict = None) -> tuple[bool, str]:
        """
        Create new user with hashed password

        Args:
            username: Username for new user
            password: Password for new user
            user_data: Optional dictionary containing additional user data
                      (e.g., email, first_name, last_name, etc.)

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Check if username exists
            if self.collection.find_one({"username": username.lower()}):
                return False, "Username already exists"

            # Check if email exists (if provided)
            if user_data and 'email' in user_data:
                if self.collection.find_one({"email": user_data['email'].lower()}):
                    return False, "Email already registered"

            # Hash password
            hashed_pw, salt = hash_password(password)

            # Get current UTC time
            current_utc = datetime.now(timezone.utc)

            # Prepare base user document
            user_document = {
                "username": username.lower(),
                "password": hashed_pw,
                "salt": salt,
                "created_at": current_utc,
                "last_login": current_utc,
                "total_workouts": 0,
                "workout_history": []
            }

            # Add additional user data if provided
            if user_data:
                # Convert email to lowercase if it exists
                if 'email' in user_data:
                    user_data['email'] = user_data['email'].lower()
                user_document.update(user_data)

            # Insert user into database
            self.collection.insert_one(user_document)
            return True, "User created successfully"

        except Exception as e:
            return False, f"Error creating user: {str(e)}"

    def validate_login(self, username: str, password: str) -> tuple[bool, dict | None]:
        """Validate user login credentials"""
        try:
            user = self.collection.find_one({"username": username.lower()})
            if user and verify_password(password, user["password"]):
                # Update last login time with UTC
                self.collection.update_one(
                    {"username": username.lower()},
                    {"$set": {"last_login": datetime.now(timezone.utc)}}
                )
                return True, user
            return False, None
        except Exception as e:
            print(f"Login validation error: {e}")
            return False, None

    def update_user_profile(self, username: str, update_data: dict) -> bool:
        """Update user profile information"""
        try:
            # Ensure email is lowercase if it's being updated
            if 'email' in update_data:
                update_data['email'] = update_data['email'].lower()

            result = self.collection.update_one(
                {"username": username.lower()},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Profile update error: {e}")
            return False
