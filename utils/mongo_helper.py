"""
MongoDB Helper Module

This module provides functions for interacting with MongoDB database
for the Fitlistic application. It handles user authentication, workout plans,
logs, and fitness data collections.
"""

from typing import Tuple, Optional, Mapping, Any, List, Dict, Union
from datetime import datetime, timezone, timedelta
import json

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import streamlit as st
import bcrypt
from bson.objectid import ObjectId

# Constants for database and collections
DB_NAME = "fitlistic"
COLLECTIONS = {
    "USERS": "users",
    "WORKOUT_PLANS": "user_workout_plans",
    "WORKOUT_LOGS": "workout_logs",
    "COMPLETED_WORKOUTS": "completed_workouts",
    "WELLBEING_SCORES": "wellbeing_scores",
    "EXERCISES": "exercises",
    "BREATHWORK": "breathwork_techniques",
    "MEDITATION": "meditation_templates",
    "STRETCHING": "stretching_routines",
    "WARM_UPS": "warm_ups",
    "COOL_DOWNS": "cool_downs"
}

# MET values for calorie calculations
MET_VALUES = {
    "warm_up": 3.5,  # Light calisthenics
    "cool_down": 2.5,  # Light stretching
    "exercise": 5.0,  # General exercise
    "stretching": 2.5,  # Stretching
    "breathwork": 2.0,  # Breathing exercises
    "meditation": 1.3,  # Sitting meditation
    "cardio": 7.0,  # Moderate cardio
    "strength": 5.0,  # Weight training
    "hiit": 8.0,  # High-intensity interval training
    "yoga": 3.0,  # Hatha yoga
    "pilates": 3.5,  # Pilates
    "unknown": 3.0  # Default value
}

# Days of the week
DAYS_OF_WEEK = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']


@st.cache_resource
def init_connection() -> Optional[MongoClient]:
    """
    Initialize MongoDB connection using cached resource.

    Returns:
        MongoClient or None: MongoDB client instance if connection successful, None otherwise
    """
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
        st.error("Database connection failed")
        return None


def get_collection(database_name: str, collection_name: str) -> Optional[Any]:
    """
    Get a MongoDB collection object.

    Args:
        database_name: Name of the database
        collection_name: Name of the collection

    Returns:
        Collection object or None if connection failed
    """
    client = init_connection()
    if client is None:
        return None
    return client[database_name][collection_name]


def hash_password(password: str) -> Tuple[bytes, bytes]:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Tuple of (hashed_password, salt)
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed, salt


def verify_password(password: str, hashed_password: bytes) -> bool:
    """
    Verify password against hashed version.

    Args:
        password: Plain text password to verify
        hashed_password: Previously hashed password

    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)


def create_user(username: str, password: str, user_data: Optional[Dict] = None) -> Tuple[bool, str]:
    """
    Create new user with hashed password.

    Args:
        username: User's username (will be converted to lowercase)
        password: User's plain text password (will be hashed)
        user_data: Additional user data like email, profile info, etc.

    Returns:
        Tuple of (success_status, message)
    """
    collection = get_collection(DB_NAME, COLLECTIONS["USERS"])
    if collection is None:
        return False, "Database connection failed"

    try:
        # Check if username exists
        existing_user = collection.find_one({"username": username.lower()})
        if existing_user is not None:
            return False, "Username already exists. Please choose another one"

        # Check if email exists
        if user_data and 'email' in user_data:
            existing_email = collection.find_one({"email": user_data['email'].lower()})
            if existing_email is not None:
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


def validate_login(username: str, password: str) -> Tuple[bool, Optional[Mapping[str, Any]]]:
    """
    Validate user login credentials.

    Args:
        username: User's username
        password: User's plain text password

    Returns:
        Tuple of (success_status, user_document or None)
    """
    collection = get_collection(DB_NAME, COLLECTIONS["USERS"])
    if collection is None:
        return False, None

    try:
        user = collection.find_one({"username": username.lower()})
        if user is not None and verify_password(password, user["password"]):
            # Update last login time
            collection.update_one(
                {"username": username.lower()},
                {"$set": {"last_login": datetime.now(timezone.utc)}}
            )
            return True, user
        return False, None
    except Exception:
        return False, None


def get_week_start_date() -> datetime:
    """
    Get the start date (Monday) of the current week.

    Returns:
        Monday 00:00:00 UTC of the current week
    """
    now = datetime.now(timezone.utc)
    # Get previous Monday (week start)
    days_since_monday = now.weekday()
    monday = now - timedelta(days=days_since_monday)
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def get_workout_logs(user_id: str, days: int = 0) -> List[Dict]:
    """
    Fetch workout logs for a given user.

    Args:
        user_id: User ID string
        days: If > 0, only fetch logs from the last 'days' days. 0 means fetch all logs.

    Returns:
        List of workout log documents
    """
    collection = get_collection(DB_NAME, COLLECTIONS["WORKOUT_LOGS"])
    if collection is None:
        return []

    query = {"user_id": ObjectId(user_id)}

    if days > 0:
        now_utc = datetime.now(timezone.utc)
        cutoff = now_utc - timedelta(days=days)
        query["date"] = {"$gte": cutoff}

    logs = list(collection.find(query).sort("date", -1))
    return logs


def get_weekly_workout_stats(user_id: str) -> Optional[Dict[str, int]]:
    """
    Compute the user's workout stats for the last 7 days.

    Args:
        user_id: User ID string

    Returns:
        Dictionary with workouts count, total minutes, and calories, or None if no workouts
    """
    collection = get_collection(DB_NAME, COLLECTIONS["WORKOUT_LOGS"])
    if collection is None:
        return None

    now_utc = datetime.now(timezone.utc)
    start_date = now_utc - timedelta(days=7)

    # Find logs for the past 7 days
    query = {
        "user_id": ObjectId(user_id),
        "date": {"$gte": start_date}
    }

    logs_cursor = collection.find(query)
    workouts_count = 0
    total_minutes = 0
    total_calories = 0

    for log in logs_cursor:
        workouts_count += 1
        total_minutes += log.get("total_duration_minutes", 0)
        total_calories += log.get("total_calories_burned", 0)

    if workouts_count == 0:
        return None

    return {
        "workouts": workouts_count,
        "minutes": total_minutes,
        "calories": total_calories
    }


def get_latest_wellbeing_score(user_id: str) -> Optional[int]:
    """
    Return the user's latest well-being score (1-5).

    Args:
        user_id: User ID string

    Returns:
        Well-being score or None if not found
    """
    collection = get_collection(DB_NAME, COLLECTIONS["WELLBEING_SCORES"])
    if collection is None:
        return None

    doc = collection.find_one(
        {"user_id": ObjectId(user_id)},
        sort=[("date", -1)]
    )

    if doc:
        return doc.get("score", None)
    return None


def save_user_plan(user_id: str, plan_data: Dict) -> Tuple[bool, str]:
    """
    Save a user's workout plan.

    Args:
        user_id: User ID string
        plan_data: Workout plan data

    Returns:
        Tuple of (success_status, message or plan_id)
    """
    collection = get_collection(DB_NAME, COLLECTIONS["WORKOUT_PLANS"])
    if collection is None:
        return False, "Database connection failed"

    try:
        # Deactivate old plans
        collection.update_many(
            {"user_id": user_id, "is_active": True},
            {"$set": {"is_active": False}}
        )

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


def save_workout_plan(user_id: str, plan_data: Dict) -> Tuple[bool, str]:
    """
    Save a workout plan to the database and mark it as active.

    Args:
        user_id: User ID string
        plan_data: Workout plan data

    Returns:
        Tuple of (success_status, message or plan_id)
    """
    try:
        collection = get_collection(DB_NAME, COLLECTIONS["WORKOUT_PLANS"])
        if collection is None:
            return False, "Could not connect to database"

        # Convert string user_id to ObjectId if necessary
        user_obj_id = ObjectId(user_id) if isinstance(user_id, str) else user_id

        # Format the plan for MongoDB
        plan_document = {
            "user_id": user_obj_id,
            "created_at": datetime.now(timezone.utc),
            "schedule": plan_data["schedule"],
            "is_active": True,
            "metadata": plan_data["metadata"]
        }

        # Deactivate all existing workout plans for this user
        collection.update_many(
            {"user_id": user_obj_id},
            {"$set": {"is_active": False}}
        )

        # Insert the new workout plan
        result = collection.insert_one(plan_document)
        return True, str(result.inserted_id)

    except Exception as e:
        return False, str(e)


def get_active_workout_plan(user_id: str) -> Optional[Dict]:
    """
    Get the user's active workout plan.

    Args:
        user_id: User ID string

    Returns:
        Active workout plan document or None if no active plan exists
    """
    try:
        # Convert user_id to ObjectId if it's a string
        user_obj_id = ObjectId(user_id) if isinstance(user_id, str) else user_id

        # Get the user's active workout plan collection
        plans_collection = get_collection(DB_NAME, COLLECTIONS["WORKOUT_PLANS"])
        if plans_collection is None:
            print("❌ Failed to connect to workout plans collection")
            return None

        # Find the active plan
        active_plan = plans_collection.find_one({
            "user_id": user_obj_id,
            "is_active": True
        })

        return active_plan

    except Exception as e:
        print(f"❌ Error retrieving active workout plan: {e}")
        import traceback
        traceback.print_exc()
        return None


def estimate_calories_burned(activity_type: str, duration_minutes: int, weight_kg: float) -> int:
    """
    Estimate calories burned based on activity type, duration, and user weight.

    Args:
        activity_type: Type of activity (e.g., "warm_up", "exercise")
        duration_minutes: Duration in minutes
        weight_kg: User's weight in kilograms

    Returns:
        Estimated calories burned (rounded to nearest integer)
    """
    # Get MET value for the activity type
    met = MET_VALUES.get(activity_type.lower(), MET_VALUES["unknown"])

    # Calculate calories: MET * weight (kg) * duration (hours)
    # 1 MET = 1 kcal/kg/hour
    hours = duration_minutes / 60
    calories = met * weight_kg * hours

    return round(calories)


def save_workout_log(
        user_id: str,
        workout_date: str,
        workout_activities: List[Dict],
        workout_type: str,
        notes: str = "",
        plan_id: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Save a completed workout to the workout_logs collection.

    Args:
        user_id: User ID string
        workout_date: Date string in YYYY-MM-DD format
        workout_activities: List of workout activity blocks
        workout_type: Type of workout (e.g., "Strength", "Cardio")
        notes: Optional notes about the workout
        plan_id: Optional ID of the workout plan this log belongs to

    Returns:
        Tuple of (success_status, message or log_id)
    """
    try:
        collection = get_collection(DB_NAME, COLLECTIONS["WORKOUT_LOGS"])
        if collection is None:
            return False, "Could not connect to database"

        # Convert string user_id to ObjectId if necessary
        user_obj_id = ObjectId(user_id) if isinstance(user_id, str) else user_id

        # Convert plan_id to ObjectId if provided
        plan_obj_id = ObjectId(plan_id) if plan_id else None

        # Handle both old format (empty workout_refs) and new format (schedule)
        if not workout_activities or (isinstance(workout_activities, list) and len(workout_activities) == 0):
            # Simple log with minimal information for old format
            workout_date_obj = datetime.strptime(workout_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            log_document = {
                "user_id": user_obj_id,
                "date": workout_date_obj,
                "total_duration_minutes": 30,  # Default duration
                "total_calories_burned": 150,  # Default calories
                "workout_notes": f"Completed {workout_type}. {notes}",
                "activities": []
            }

            # Add plan_id if provided
            if plan_obj_id:
                log_document["plan_id"] = plan_obj_id

            result = collection.insert_one(log_document)
            return True, str(result.inserted_id)

        # Calculate total duration and estimated calories for the new format
        total_duration = sum(block.get('duration', 0) for block in workout_activities)

        # Get user weight for calorie estimation
        user_collection = get_collection(DB_NAME, COLLECTIONS["USERS"])
        user = user_collection.find_one({"_id": user_obj_id})
        user_weight = user.get('weight', 70) if user else 70  # Default to 70kg if not found

        # Calculate estimated calories
        total_calories = 0
        activities_log = []

        for block in workout_activities:
            activity = block.get('activity', {})
            if not activity:
                continue

            activity_type = activity.get('type', 'unknown')
            activity_id = str(activity.get('_id', ''))
            duration = block.get('duration', 0)

            # Add to activities log
            activities_log.append({
                "collection_name": activity_type,
                "exercise_id": activity_id,
                "duration_minutes": duration,
                "notes": ""
            })

            # Add to calorie count
            total_calories += estimate_calories_burned(activity_type, duration, user_weight)

        # Create workout log document
        workout_date_obj = datetime.strptime(workout_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        log_document = {
            "user_id": user_obj_id,
            "date": workout_date_obj,
            "total_duration_minutes": total_duration,
            "total_calories_burned": total_calories,
            "workout_notes": f"Completed {workout_type}. {notes}",
            "activities": activities_log
        }

        # Add plan_id if provided
        if plan_obj_id:
            log_document["plan_id"] = plan_obj_id

        # Insert the workout log
        result = collection.insert_one(log_document)
        return True, str(result.inserted_id)

    except Exception as e:
        return False, str(e)


def mark_workout_as_completed(user_id: Union[str, ObjectId], day_of_week: str) -> Tuple[bool, str]:
    """
    Mark a workout as completed for the current week.

    Args:
        user_id: User ID string or ObjectId
        day_of_week: Day of the week (e.g., "monday", "tuesday")

    Returns:
        Tuple of (success_status, message)
    """
    collection = get_collection(DB_NAME, COLLECTIONS["COMPLETED_WORKOUTS"])
    if collection is None:
        return False, "Database connection failed"

    user_obj_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
    day = day_of_week.lower()

    # Record the completion
    completion_doc = {
        "user_id": user_obj_id,
        "day_of_week": day,
        "completed_at": datetime.now(timezone.utc),
        "week_start_date": get_week_start_date()
    }

    try:
        # First check if already completed this week
        existing = collection.find_one({
            "user_id": user_obj_id,
            "day_of_week": day,
            "week_start_date": get_week_start_date()
        })

        if existing:
            # Already marked as completed
            return True, "Already completed"

        # Insert new completion record
        result = collection.insert_one(completion_doc)
        return bool(result.inserted_id), "Workout marked as completed"

    except Exception as e:
        print(f"Error marking workout as completed: {e}")
        return False, str(e)


def is_workout_completed(user_id: Union[str, ObjectId], day_of_week: str) -> bool:
    """
    Check if a workout is completed for the current week.

    Args:
        user_id: User ID string or ObjectId
        day_of_week: Day of the week (e.g., "monday", "tuesday")

    Returns:
        True if workout is completed, False otherwise
    """
    collection = get_collection(DB_NAME, COLLECTIONS["COMPLETED_WORKOUTS"])
    if collection is None:
        return False

    user_obj_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
    day = day_of_week.lower()

    # Check if workout is completed for the current week
    existing = collection.find_one({
        "user_id": user_obj_id,
        "day_of_week": day,
        "week_start_date": get_week_start_date()
    })

    return existing is not None


def get_workout_for_day(workout_plan: Optional[Dict], day_of_week: str) -> Optional[Dict]:
    """
    Get workout details for a specific day from a workout plan.

    Args:
        workout_plan: Workout plan document
        day_of_week: Day of the week (e.g., "monday", "tuesday")

    Returns:
        Workout details for the specified day or None
    """
    if workout_plan is None:
        return None

    return workout_plan['schedule'].get(day_of_week.lower())


def get_next_incomplete_workout_day(user_id: str, workout_plan: Optional[Dict]) -> Optional[str]:
    """
    Find the next day with an incomplete workout.

    Args:
        user_id: User ID string
        workout_plan: Workout plan document

    Returns:
        Next day with an incomplete workout or None if all workouts are completed
    """
    if workout_plan is None:
        return None

    today = datetime.now().strftime("%A").lower()
    today_index = DAYS_OF_WEEK.index(today)

    for i in range(1, 8):
        next_index = (today_index + i) % 7
        next_day = DAYS_OF_WEEK[next_index]

        if next_day not in workout_plan['schedule']:
            continue

        if is_workout_completed(user_id, next_day):
            continue

        return next_day

    return None


def initialize_fitness_collections() -> bool:
    """
    Initialize fitness-related collections with sample data if they are empty.

    Returns:
        True if initialization was successful or collections already had data, 
        False if there was an error
    """
    client = init_connection()
    if client is None:
        return False

    db = client[DB_NAME]

    try:
        collections_data = {
            COLLECTIONS["EXERCISES"]: 'exercises.json',
            COLLECTIONS["BREATHWORK"]: 'breathwork_techniques.json',
            COLLECTIONS["MEDITATION"]: 'meditation_templates.json',
            COLLECTIONS["STRETCHING"]: 'stretching_routines.json',
            COLLECTIONS["WARM_UPS"]: 'warm_ups.json',
            COLLECTIONS["COOL_DOWNS"]: 'cool_downs.json'
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
