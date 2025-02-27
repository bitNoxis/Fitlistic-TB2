from typing import Tuple, Optional, Mapping, Any

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import streamlit as st
import bcrypt
from datetime import datetime, timezone, timedelta
import json
from bson.objectid import ObjectId  # For working with _id as an ObjectId


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
        st.error("Database connection failed")
        return None


def get_collection(database_name: str, collection_name: str):
    client = init_connection()
    if client is None:
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
    collection = get_collection("fitlistic", "users")
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


# -----------------------------
# NEW HELPER FUNCTIONS FOR OVERVIEW
# -----------------------------

def get_workout_logs(user_id: str, days: int = 0):
    """
    Fetch workout logs for a given user. If 'days' > 0, only fetch logs
    from the last 'days' days. Otherwise fetch all logs.
    """
    collection = get_collection("fitlistic", "workout_logs")
    if collection is None:
        return []
    query = {"user_id": ObjectId(user_id)}  # store user._id as ObjectId in DB
    if days > 0:
        now_utc = datetime.now(timezone.utc)
        cutoff = now_utc - timedelta(days=days)
        query["date"] = {"$gte": cutoff}
    logs = list(collection.find(query).sort("date", -1))
    return logs


def get_weekly_workout_stats(user_id: str) -> dict | None:
    """
    Compute the user's workout stats (count, total minutes, total calories)
    for the last 7 days. Returns None if no data or DB error.
    """
    collection = get_collection("fitlistic", "workout_logs")
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


def get_latest_wellbeing_score(user_id: str):
    """
    Return the user's latest well-being score (1-5), or None if not found.
    """
    collection = get_collection("fitlistic", "wellbeing_scores")
    if collection is None:
        return None
    doc = collection.find_one(
        {"user_id": ObjectId(user_id)},
        sort=[("date", -1)]
    )
    if doc:
        return doc.get("score", None)
    return None


# -----------------------------
# Additional functions for saving user plan, etc. remain the same
# -----------------------------

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


def save_workout_plan(user_id, plan_data):
    """Save a workout plan to the database and mark it as active."""
    try:
        collection = get_collection("fitlistic", "user_workout_plans")
        if collection is None:
            return False, "Could not connect to database"

        # Format the plan for MongoDB
        plan_document = {
            "user_id": ObjectId(user_id),
            "created_at": datetime.now(timezone.utc),
            "schedule": plan_data["schedule"],
            "is_active": True,
            "metadata": plan_data["metadata"]
        }

        # Deactivate all existing workout plans for this user
        collection.update_many(
            {"user_id": ObjectId(user_id)},
            {"$set": {"is_active": False}}
        )

        # Insert the new workout plan
        result = collection.insert_one(plan_document)

        return True, str(result.inserted_id)
    except Exception as e:
        return False, str(e)


def get_active_workout_plan(user_id):
    """Retrieve the user's active workout plan."""
    try:
        collection = get_collection("fitlistic", "user_workout_plans")
        if collection is None:
            return None

        # Find the active workout plan for this user
        plan = collection.find_one({
            "user_id": ObjectId(user_id),
            "is_active": True
        })

        return plan
    except Exception as e:
        st.error(f"Error retrieving workout plan: {str(e)}")
        return None


def save_workout_log(user_id, workout_date, workout_activities, workout_type, notes=""):
    """Save a completed workout to the workout_logs collection."""
    try:
        collection = get_collection("fitlistic", "workout_logs")
        if collection is None:
            return False, "Could not connect to database"

        # Handle both old format (empty workout_refs) and new format (schedule)
        if not workout_activities or (isinstance(workout_activities, list) and len(workout_activities) == 0):
            # Simple log with minimal information for old format
            workout_date_obj = datetime.strptime(workout_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            log_document = {
                "user_id": ObjectId(user_id),
                "date": workout_date_obj,
                "total_duration_minutes": 30,  # Default duration
                "total_calories_burned": 150,  # Default calories
                "workout_notes": f"Completed {workout_type}. {notes}",
                "activities": []
            }
            result = collection.insert_one(log_document)
            return True, str(result.inserted_id)

        # Calculate total duration and estimated calories for the new format
        total_duration = sum(block.get('duration', 0) for block in workout_activities)

        # Get user weight for calorie estimation
        user_collection = get_collection("fitlistic", "users")
        user = user_collection.find_one({"_id": ObjectId(user_id)})
        user_weight = user.get('weight', 70) if user else 70

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
            "user_id": ObjectId(user_id),
            "date": workout_date_obj,
            "total_duration_minutes": total_duration,
            "total_calories_burned": total_calories,
            "workout_notes": f"Completed {workout_type}. {notes}",
            "activities": activities_log
        }

        # Insert the workout log
        result = collection.insert_one(log_document)

        return True, str(result.inserted_id)
    except Exception as e:
        return False, str(e)


def estimate_calories_burned(activity_type, duration_minutes, weight_kg):
    """Estimate calories burned based on activity type, duration, and user weight."""
    # MET values (Metabolic Equivalent of Task) for different activities
    met_values = {
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

    # Get MET value for the activity type
    met = met_values.get(activity_type.lower(), met_values["unknown"])

    # Calculate calories: MET * weight (kg) * duration (hours)
    # 1 MET = 1 kcal/kg/hour
    hours = duration_minutes / 60
    calories = met * weight_kg * hours

    return round(calories)


def mark_workout_as_completed(user_id, day_of_week):
    from bson.objectid import ObjectId
    from datetime import datetime, timezone

    collection = get_collection("fitlistic", "completed_workouts")
    if collection is None:
        return False, "Database connection failed"

    user_obj_id = ObjectId(user_id) if isinstance(user_id, str) else user_id

    # Record the completion
    completion_doc = {
        "user_id": user_obj_id,
        "day_of_week": day_of_week.lower(),
        "completed_at": datetime.now(timezone.utc),
        "week_start_date": get_week_start_date()
    }

    try:
        # First check if already completed this week
        existing = collection.find_one({
            "user_id": user_obj_id,
            "day_of_week": day_of_week.lower(),
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


def get_week_start_date():
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    # Get previous Monday (week start)
    days_since_monday = now.weekday()
    monday = now - timedelta(days=days_since_monday)
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def is_workout_completed(user_id, day_of_week):
    from bson.objectid import ObjectId

    collection = get_collection("fitlistic", "completed_workouts")
    if collection is None:
        return False

    user_obj_id = ObjectId(user_id) if isinstance(user_id, str) else user_id

    # Check if workout is completed for the current week
    existing = collection.find_one({
        "user_id": user_obj_id,
        "day_of_week": day_of_week.lower(),
        "week_start_date": get_week_start_date()
    })

    return existing is not None


def get_workout_for_day(workout_plan, day_of_week):
    if workout_plan is None:
        return None

    return workout_plan['schedule'].get(day_of_week.lower())


def get_next_incomplete_workout_day(user_id, workout_plan):
    from datetime import datetime, timedelta

    if workout_plan is None:
        return None

    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    today = datetime.now().strftime("%A").lower()
    today_index = days.index(today)

    for i in range(1, 8):
        next_index = (today_index + i) % 7
        next_day = days[next_index]

        if next_day not in workout_plan['schedule']:
            continue

        if is_workout_completed(user_id, next_day):
            continue

        return next_day

    return None


def get_active_workout_plan(user_id: str) -> dict | None:
    """
    Get the user's active workout plan.
    Returns None if no active plan exists.
    """
    try:
        # Convert user_id to ObjectId if it's a string
        from bson import ObjectId
        user_obj_id = ObjectId(user_id)

        # Get the user's active workout plan collection
        plans_collection = get_collection("fitlistic", "user_workout_plans")
        if plans_collection is None:
            print("❌ Failed to connect to workout plans collection")
            return None

        # Find the active plan
        active_plan = plans_collection.find_one({
            "user_id": user_obj_id,
            "is_active": True
        })

        if active_plan is None:
            print(f"❌ No active plan found for user {user_id}")
            return None

        # Return the plan as is - we'll handle workout details in the display function
        return active_plan

    except Exception as e:
        print(f"❌ Error retrieving active workout plan: {e}")
        import traceback
        traceback.print_exc()
        return None


def initialize_fitness_collections():
    """Initialize fitness-related collections with sample data"""
    client = init_connection()
    if client is None:
        return False

    db = client['fitlistic']

    try:
        collections_data = {
            'exercises': 'exercises.json',
            'breathwork_techniques': 'breathwork_techniques.json',
            'meditation_templates': 'meditation_templates.json',
            'stretching_routines': 'stretching_routines.json',
            'warm_ups': 'warm_ups.json',
            'cool_downs': 'cool_downs.json'
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
