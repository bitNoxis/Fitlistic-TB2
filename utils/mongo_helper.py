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


def save_workout_plan(user_id: str, plan_data: dict) -> tuple[bool, str]:
    """
    Save a workout plan with exercise references to MongoDB.
    Overwrites any existing active plan and clears old workout logs.

    Args:
        user_id: User's ID string
        plan_data: Dictionary containing workout plan from AI Coach

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Ensure user_id is converted to ObjectId
        from bson.objectid import ObjectId
        from datetime import datetime, timezone

        user_obj_id = ObjectId(user_id)

        collection = get_collection("fitlistic", "user_workout_plans")
        if collection is None:
            return False, "Database connection failed"

        # Deactivate any currently active plans
        collection.update_many(
            {"user_id": user_obj_id},
            {"$set": {"is_active": False}}
        )

        # Clear workout logs that might be referencing a previous plan
        logs_collection = get_collection("fitlistic", "workout_logs")
        if logs_collection is not None:  # Use explicit comparison with None
            # Get current week's start
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone.utc)
            days_since_monday = now.weekday()
            week_start = (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0)

            # Remove logs from current week
            logs_collection.delete_many({
                "user_id": user_obj_id,
                "date": {"$gte": week_start}
            })

        # Convert schedule to reference format
        reference_schedule = {}

        for day, day_data in plan_data['schedule'].items():
            reference_schedule[day] = {
                'type': day_data['type'],
                'workout_refs': []
            }

            # Process each activity in the day's schedule
            for activity in day_data.get('schedule', []):
                activity_data = activity.get('activity', {})
                duration = activity.get('duration', 0)

                # Create workout reference with type detection
                workout_ref = {
                    'duration': duration
                }

                # Determine activity type
                def determine_activity_type(activity_data):
                    if 'type' in activity_data:
                        activity_type = activity_data['type'].lower()
                        if 'breathwork' in activity_type:
                            return 'breathwork'
                        elif 'warm' in activity_type or 'warm_up' in activity_type:
                            return 'warm_up'
                        elif 'cool' in activity_type or 'cool_down' in activity_type:
                            return 'cool_down'
                        elif 'stretch' in activity_type:
                            return 'stretching'
                        elif 'meditation' in activity_type:
                            return 'meditation'
                        elif 'exercise' in activity_type:
                            return 'exercise'

                    name = activity_data.get('name', '').lower()
                    if 'breath' in name:
                        return 'breathwork'
                    elif 'warm' in name:
                        return 'warm_up'
                    elif 'cool' in name:
                        return 'cool_down'
                    elif 'stretch' in name:
                        return 'stretching'
                    elif 'meditation' in name:
                        return 'meditation'

                    if 'sequence' in activity_data:
                        if 'warm' in name:
                            return 'warm_up'
                        elif 'cool' in name:
                            return 'cool_down'
                        else:
                            return 'stretching'
                    elif 'steps' in activity_data:
                        if 'meditation' in name:
                            return 'meditation'
                        elif 'breath' in name:
                            return 'breathwork'
                        else:
                            return 'breathwork'
                    elif 'form_cues' in activity_data:
                        return 'exercise'

                    return 'unknown'

                try:
                    activity_id = activity_data.get('_id')

                    if activity_id:
                        workout_ref['reference_id'] = ObjectId(str(activity_id))

                    # Set the activity type ONCE and don't override it
                    workout_ref['activity_type'] = determine_activity_type(activity_data)

                    # Only add to workout_refs if we have both type and ID
                    if 'reference_id' in workout_ref and 'activity_type' in workout_ref:
                        reference_schedule[day]['workout_refs'].append(workout_ref)

                except Exception as id_error:
                    print(f"Error processing activity ID: {id_error}")
                    print("Problematic activity data:", activity_data)

        # Create the plan document
        plan_document = {
            "user_id": user_obj_id,
            "created_at": datetime.now(timezone.utc),
            "schedule": reference_schedule,
            "is_active": True,
            # Include metadata from original plan
            "metadata": plan_data.get('metadata', {})
        }

        result = collection.insert_one(plan_document)
        if result.inserted_id:
            return True, "Plan saved successfully"
        return False, "Failed to save plan"

    except Exception as e:
        import traceback
        print(f"Error saving plan: {e}")
        print(traceback.format_exc())
        return False, f"Error saving plan: {str(e)}"


def estimate_calories_burned(exercise_type, duration_minutes, user_weight):
    met_values = {
        'warm_up': 3.0,
        'cool_down': 2.5,
        'exercise': 5.0,
        'breathwork': 2.0,
        'meditation': 1.5,
        'stretching': 2.5,
        'unknown': 3.0
    }

    duration_hours = duration_minutes / 60
    weight_kg = user_weight if user_weight else 70
    met = met_values.get(exercise_type, 3.0)
    calories = met * weight_kg * duration_hours

    return round(calories)


def save_workout_log(user_id, workout_refs, workout_type, notes=""):
    try:
        from bson.objectid import ObjectId
        from datetime import datetime, timezone

        user_obj_id = ObjectId(user_id)
        collection = get_collection("fitlistic", "workout_logs")

        if collection is None:
            return False, "Database connection failed"

        total_duration = sum(ref['duration'] for ref in workout_refs)

        users_collection = get_collection("fitlistic", "users")
        user = users_collection.find_one({"_id": user_obj_id})
        user_weight = user.get('weight', 70) if user else 70

        total_calories = sum(
            estimate_calories_burned(ref['activity_type'], ref['duration'], user_weight)
            for ref in workout_refs
        )

        activities = []
        collection_mapping = {
            'warm_up': 'warm_ups',
            'cool_down': 'cool_downs',
            'exercise': 'exercises',
            'breathwork': 'breathwork_techniques',
            'meditation': 'meditation_templates',
            'stretching': 'stretching_routines'
        }

        for ref in workout_refs:
            collection_name = collection_mapping.get(ref['activity_type'], 'exercises')

            # Get exercise name from the exercise_details if available
            exercise_name = "Exercise"
            if 'exercise_details' in ref and 'name' in ref['exercise_details']:
                exercise_name = ref['exercise_details']['name']

            activities.append({
                "collection_name": collection_name,
                "exercise_id": ref['reference_id'],
                "duration_minutes": ref['duration'],
                "notes": exercise_name
            })

        log_document = {
            "user_id": user_obj_id,
            "date": datetime.now(timezone.utc),
            "total_duration_minutes": total_duration,
            "total_calories_burned": total_calories,
            "workout_notes": f"Completed {workout_type} workout",
            "activities": activities
        }

        if notes:
            log_document["workout_notes"] += f": {notes}"

        result = collection.insert_one(log_document)

        if result.inserted_id:
            users_collection.update_one(
                {"_id": user_obj_id},
                {"$inc": {"total_workouts": 1}}
            )

            return True, str(result.inserted_id)

        return False, "Failed to save workout log"

    except Exception as e:
        import traceback
        print(f"Error saving workout log: {e}")
        print(traceback.format_exc())
        return False, f"Error saving workout log: {str(e)}"


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
    Get the user's active workout plan with full exercise details.
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

            # Optional: Debug print to see what plans exist
            all_plans = list(plans_collection.find({"user_id": user_obj_id}))
            print("Existing plans:")
            for plan in all_plans:
                print(f"Plan ID: {plan.get('_id')}, Active: {plan.get('is_active')}")
            return None

        # Print the raw plan structure for debugging
        import json
        print("Raw Active Plan:")
        print(json.dumps(active_plan, default=str, indent=2))

        # Prepare collections for loading full exercise details
        collections = {
            "exercises": get_collection("fitlistic", "exercises"),
            "warm_ups": get_collection("fitlistic", "warm_ups"),
            "cool_downs": get_collection("fitlistic", "cool_downs"),
            "breathwork_techniques": get_collection("fitlistic", "breathwork_techniques"),
            "meditation_templates": get_collection("fitlistic", "meditation_templates"),
            "stretching_routines": get_collection("fitlistic", "stretching_routines")
        }

        # Enrich the schedule with full exercise details
        enriched_schedule = {}
        for day, day_data in active_plan['schedule'].items():
            enriched_schedule[day] = {
                'type': day_data['type'],
                'workout_refs': []
            }

            for workout_ref in day_data.get('workout_refs', []):
                try:
                    # Determine the correct collection based on activity type
                    collection_map = {
                        'warm_up': 'warm_ups',
                        'cool_down': 'cool_downs',
                        'exercise': 'exercises',
                        'breathwork': 'breathwork_techniques',
                        'meditation': 'meditation_templates',
                        'stretching': 'stretching_routines'
                    }

                    collection_name = collection_map.get(workout_ref.get('activity_type', 'exercise'), 'exercises')
                    collection = collections[collection_name]

                    # Try to fetch the full exercise details
                    exercise = collection.find_one({"_id": workout_ref['reference_id']})

                    if exercise:
                        enriched_workout_ref = workout_ref.copy()
                        enriched_workout_ref['exercise_details'] = exercise
                        enriched_schedule[day]['workout_refs'].append(enriched_workout_ref)
                    else:
                        print(f"❌ No exercise found for {workout_ref}")

                except Exception as e:
                    print(f"Error processing workout ref: {e}")

        # Create the enriched plan
        enriched_plan = {
            'metadata': active_plan.get('metadata', {}),
            'schedule': enriched_schedule,
            'is_active': active_plan.get('is_active', True)
        }

        # Print the enriched plan structure
        print("Enriched Active Plan:")
        print(json.dumps(enriched_plan, default=str, indent=2))

        return enriched_plan

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
