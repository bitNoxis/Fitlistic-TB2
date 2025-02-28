"""
Workout Plan Generator

This module provides functions to generate personalized workout plans based on user
data and preferences. It fetches appropriate exercises, warm-ups, cool-downs, 
meditation, stretching routines and breathwork activities from collections and assembles them into
daily and weekly schedules.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

# Constants for workout configuration
WORKOUT_DURATIONS = [15, 30, 45, 60]
DEFAULT_WORKOUT_DURATION = 30
DEFAULT_WARMUP_TIMES = {15: 4, 30: 5, 45: 5, 60: 7}
DEFAULT_BREATHWORK_TIMES = {15: 0, 30: 3, 45: 5, 60: 5}
DEFAULT_COOLDOWN_TIMES = {15: 4, 30: 5, 45: 5, 60: 7}
DEFAULT_MEDITATION_TIMES = {15: 3, 30: 5, 45: 5, 60: 7}
DEFAULT_STRETCHING_TIMES = {15: 0, 30: 0, 45: 0, 60: 10}
DEFAULT_EXERCISE_COUNTS = {15: 2, 30: 2, 45: 4, 60: 4}

# Define difficulty levels
DIFFICULTY_LEVELS = ['beginner', 'intermediate', 'advanced']

# Collection types
COLLECTION_TYPES = ['exercises', 'warm_ups', 'cool_downs', 'stretching', 'meditation', 'breathwork']

# Global cache to avoid re-fetching data
template_cache = {}


def validate_user_data(user_data: Dict) -> None:
    """
    Validate required user data fields for workout plan generation.

    Args:
        user_data: Dictionary containing user profile and preferences

    Raises:
        ValueError: If required fields are missing or invalid
    """
    required_fields = [
        'weight', 'height', 'fitness_goals', 'experience_level',
        'preferred_rest_day', 'workout_duration', 'start_date', 'date_range'
    ]

    # Check for missing fields
    missing_fields = [field for field in required_fields if field not in user_data]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    # Validate field types and values
    if not isinstance(user_data['fitness_goals'], list):
        raise ValueError("fitness_goals must be a list")

    if user_data['experience_level'] not in DIFFICULTY_LEVELS:
        raise ValueError(f"experience_level must be one of: {', '.join(DIFFICULTY_LEVELS)}")

    if user_data['workout_duration'] not in WORKOUT_DURATIONS:
        raise ValueError(f"workout_duration must be one of: {WORKOUT_DURATIONS}")

    # Validate date_range
    if not isinstance(user_data['date_range'], list) or len(user_data['date_range']) != 7:
        raise ValueError("date_range must be a list of 7 date strings")


def add_minutes(time, minutes):
    """
    Add minutes to a datetime object.

    Args:
        time: Datetime object
        minutes: Number of minutes to add

    Returns:
        Datetime with added minutes
    """
    return time + timedelta(minutes=minutes)


def get_component_durations(total_workout_time: int) -> Dict[str, int]:
    """
    Calculate the duration for each workout component based on total workout time.

    Args:
        total_workout_time: Total workout duration in minutes

    Returns:
        Dictionary with duration for each component
    """
    workout_time = min(max(total_workout_time, min(WORKOUT_DURATIONS)), max(WORKOUT_DURATIONS))

    durations = {
        'warmup_time': DEFAULT_WARMUP_TIMES.get(workout_time, 5),
        'breathwork_time': DEFAULT_BREATHWORK_TIMES.get(workout_time, 0),
        'cooldown_time': DEFAULT_COOLDOWN_TIMES.get(workout_time, 5),
        'meditation_time': DEFAULT_MEDITATION_TIMES.get(workout_time, 5),
        'stretching_time': DEFAULT_STRETCHING_TIMES.get(workout_time, 0),
        'max_exercises': DEFAULT_EXERCISE_COUNTS.get(workout_time, 2)
    }

    # Determine whether to include optional components
    durations['include_stretching'] = durations['stretching_time'] > 0
    durations['include_breathwork'] = durations['breathwork_time'] > 0

    return durations


def select_activity_with_seed(activities: List[Dict], seed_base: int, offset: int = 0) -> Optional[Dict]:
    """
    Select an activity using a consistent seed for reproducibility.

    Args:
        activities: List of activities to choose from
        seed_base: Base value for the random seed
        offset: Offset to add to seed_base for variation

    Returns:
        Selected activity or None if list is empty
    """
    if not activities or len(activities) == 0:
        return None

    # Use the seed for consistent but varied selection
    random.seed(seed_base + offset)
    activity = random.choice(activities)
    random.seed()  # Reset random seed

    return activity


def prepare_warmup_component(warmups: List[Dict], seed_base: int, warmup_time: int) -> Optional[Dict]:
    """
    Prepare a warm-up component for the workout schedule.

    Args:
        warmups: List of warm-up activities
        seed_base: Base value for the random seed
        warmup_time: Duration in minutes

    Returns:
        Dictionary with warm-up activity and duration, or None
    """
    warmup = select_activity_with_seed(warmups, seed_base, 0)
    if not warmup:
        return None

    return {
        'activity': {
            '_id': warmup.get('_id'),
            'name': warmup.get('name', 'Warm-Up'),
            'phases': warmup.get('phases', []),
            'instructions': warmup.get('instructions', []),
            'benefits': warmup.get('benefits', []),
            'target_areas': warmup.get('target_areas', []),
            'type': 'warm_up',
            'equipment_needed': warmup.get('equipment_needed', 'None'),
            'target_heart_rate': warmup.get('target_heart_rate', '')
        },
        'duration': warmup_time
    }


def prepare_breathwork_component(breathwork_list: List[Dict], seed_base: int, breathwork_time: int) -> Optional[Dict]:
    """
    Prepare a breathwork component for the workout schedule.

    Args:
        breathwork_list: List of breathwork activities
        seed_base: Base value for the random seed
        breathwork_time: Duration in minutes

    Returns:
        Dictionary with breathwork activity and duration, or None
    """
    breath = select_activity_with_seed(breathwork_list, seed_base, 1)
    if not breath:
        return None

    return {
        'activity': {
            '_id': breath.get('_id'),
            'name': breath.get('name', 'Breathwork'),
            'steps': breath.get('steps', []),
            'instructions': breath.get('instructions', []),
            'benefits': breath.get('benefits', []),
            'type': 'breathwork'
        },
        'duration': breathwork_time
    }


def prepare_exercise_components(
        exercises: List[Dict],
        time_per_exercise: int,
        difficulty_level: str,
        max_count: int
) -> List[Dict]:
    """
    Prepare exercise components for the workout schedule.

    Args:
        exercises: List of exercise activities
        time_per_exercise: Duration in minutes per exercise
        difficulty_level: User's experience level
        max_count: Maximum number of exercises to include

    Returns:
        List of dictionaries with exercise activities and durations
    """
    result = []
    exercise_count = min(len(exercises), max_count)

    for ex in exercises[:exercise_count]:
        # If the specific difficulty level isn't available, try to fall back
        effective_level = difficulty_level
        if effective_level not in ex.get('difficulty_levels', {}):
            if 'intermediate' in ex.get('difficulty_levels', {}) and effective_level == 'advanced':
                effective_level = 'intermediate'
            elif 'beginner' in ex.get('difficulty_levels', {}):
                effective_level = 'beginner'
            else:
                effective_level = next(iter(ex.get('difficulty_levels', {}).keys()), None)

        if effective_level:
            result.append({
                'activity': {
                    '_id': ex.get('_id'),
                    'name': ex.get('name', 'Unnamed Exercise'),
                    'exercises': [{
                        'name': ex.get('name', 'Unnamed Exercise'),
                        'form_cues': ex.get('form_cues', []),
                        'sets': ex['difficulty_levels'][effective_level].get('sets', 'N/A'),
                        'reps': ex['difficulty_levels'][effective_level].get('reps', 'N/A'),
                        'target_muscles': ex.get('target_muscles', [])
                    }],
                    'type': 'exercise'
                },
                'duration': time_per_exercise
            })

    return result


def prepare_stretching_component(stretching_list: List[Dict], seed_base: int, stretching_time: int) -> Optional[Dict]:
    """
    Prepare a stretching component for the workout schedule.

    Args:
        stretching_list: List of stretching activities
        seed_base: Base value for the random seed
        stretching_time: Duration in minutes

    Returns:
        Dictionary with stretching activity and duration, or None
    """
    stretch = select_activity_with_seed(stretching_list, seed_base, 2)
    if not stretch:
        return None

    return {
        'activity': {
            '_id': stretch.get('_id'),
            'name': stretch.get('name', 'Stretching'),
            'sequence': stretch.get('sequence', []),
            'instructions': stretch.get('instructions', []),
            'benefits': stretch.get('benefits', []),
            'target_areas': stretch.get('target_areas', []),
            'type': 'stretching'
        },
        'duration': stretching_time
    }


def prepare_cooldown_component(cooldowns: List[Dict], seed_base: int, cooldown_time: int) -> Optional[Dict]:
    """
    Prepare a cool-down component for the workout schedule.

    Args:
        cooldowns: List of cool-down activities
        seed_base: Base value for the random seed
        cooldown_time: Duration in minutes

    Returns:
        Dictionary with cool-down activity and duration, or None
    """
    cooldown = select_activity_with_seed(cooldowns, seed_base, 3)
    if not cooldown:
        return None

    return {
        'activity': {
            '_id': cooldown.get('_id'),
            'name': cooldown.get('name', 'Cool-Down'),
            'phases': cooldown.get('phases', []),
            'instructions': cooldown.get('instructions', []),
            'benefits': cooldown.get('benefits', []),
            'target_areas': cooldown.get('target_areas', []),
            'type': 'cool_down',
            'equipment_needed': cooldown.get('equipment_needed', 'None'),
            'target_heart_rate': cooldown.get('target_heart_rate', '')
        },
        'duration': cooldown_time
    }


def prepare_meditation_component(meditations: List[Dict], seed_base: int, meditation_time: int) -> Optional[Dict]:
    """
    Prepare a meditation component for the workout schedule.

    Args:
        meditations: List of meditation activities
        seed_base: Base value for the random seed
        meditation_time: Duration in minutes

    Returns:
        Dictionary with meditation activity and duration, or None
    """
    meditation = select_activity_with_seed(meditations, seed_base, 4)
    if not meditation:
        return None

    return {
        'activity': {
            '_id': meditation.get('_id'),
            'name': meditation.get('name', 'Meditation'),
            'steps': meditation.get('steps', []),
            'benefits': meditation.get('benefits', []),
            'type': 'meditation'
        },
        'duration': meditation_time
    }


def create_day_schedule(user_data: Dict, collections: Dict, is_rest_day: bool, day_date: str) -> List[Dict]:
    """
    Create a daily schedule by combining items from multiple collections.

    Args:
        user_data: Dictionary with user preferences
        collections: Dictionary of MongoDB collections
        is_rest_day: Boolean indicating if this is a rest day
        day_date: Date string for the schedule

    Returns:
        List of activities for the day's schedule
    """
    if is_rest_day:
        return []

    # Get workout duration parameters
    total_workout_time = user_data.get('workout_duration', DEFAULT_WORKOUT_DURATION)
    durations = get_component_durations(total_workout_time)

    # Create schedule template to fill in proper order
    schedule_template = {
        'warm_up': None,
        'breathwork': None,
        'main_exercises': [],
        'stretching': None,
        'cool_down': None,
        'meditation': None
    }

    # Use day_date as seed for selections
    day_seed_base = sum(ord(c) for c in day_date)

    # 1. Fetch and prepare Warm-Up
    warmups = fetch_warm_ups(user_data, collections, day_date)
    if warmups:
        schedule_template['warm_up'] = prepare_warmup_component(
            warmups,
            day_seed_base,
            durations['warmup_time']
        )

    # 2. Fetch and prepare Breathwork
    if durations['include_breathwork']:
        breathwork = fetch_breathwork(user_data['experience_level'], collections, day_date)
        if breathwork:
            schedule_template['breathwork'] = prepare_breathwork_component(
                breathwork,
                day_seed_base,
                durations['breathwork_time']
            )

    # 3. Fetch and prepare Main Exercises
    main_exercises = fetch_exercises(user_data, collections, day_date)

    # Calculate remaining time for main exercises after other components
    auxiliary_time = (
            (durations['warmup_time'] if schedule_template['warm_up'] else 0) +
            (durations['breathwork_time'] if schedule_template['breathwork'] else 0) +
            durations['cooldown_time'] +
            durations['meditation_time'] +
            (durations['stretching_time'] if durations['include_stretching'] else 0)
    )

    remaining_time = total_workout_time - auxiliary_time
    exercise_count = min(len(main_exercises), durations['max_exercises'])

    if exercise_count > 0:
        time_per_exercise = max(5, remaining_time // exercise_count)
        schedule_template['main_exercises'] = prepare_exercise_components(
            main_exercises,
            time_per_exercise,
            user_data['experience_level'],
            exercise_count
        )

    # 4. Fetch and prepare Stretching
    if durations['include_stretching']:
        stretching = fetch_stretching(user_data, collections, day_date)
        if stretching:
            schedule_template['stretching'] = prepare_stretching_component(
                stretching,
                day_seed_base,
                durations['stretching_time']
            )

    # 5. Fetch and prepare Cool-down
    cooldowns = fetch_cool_downs(user_data, collections, day_date)
    if cooldowns:
        schedule_template['cool_down'] = prepare_cooldown_component(
            cooldowns,
            day_seed_base,
            durations['cooldown_time']
        )

    # 6. Fetch and prepare Meditation
    meditations = fetch_meditations(user_data['experience_level'], collections, day_date)
    if meditations:
        schedule_template['meditation'] = prepare_meditation_component(
            meditations,
            day_seed_base,
            durations['meditation_time']
        )

    # Build final schedule in correct order
    daily_schedule = []

    if schedule_template['warm_up']:
        daily_schedule.append(schedule_template['warm_up'])
    if schedule_template['breathwork']:
        daily_schedule.append(schedule_template['breathwork'])

    daily_schedule.extend(schedule_template['main_exercises'])

    if schedule_template['stretching']:
        daily_schedule.append(schedule_template['stretching'])
    if schedule_template['cool_down']:
        daily_schedule.append(schedule_template['cool_down'])
    if schedule_template['meditation']:
        daily_schedule.append(schedule_template['meditation'])

    return daily_schedule


def create_weekly_schedule(user_data: dict, collections: dict) -> dict:
    """
    Create a weekly schedule based on user data and valid items from local DB.

    Args:
        user_data: Dictionary with user preferences
        collections: Dictionary of MongoDB collections

    Returns:
        Dictionary with daily schedules for a week
    """
    date_range = user_data.get('date_range', [])
    schedule = {}

    # Get preferred rest day from user data
    preferred_rest_day = user_data.get('preferred_rest_day')

    for date in date_range:
        is_rest_day = date == preferred_rest_day
        schedule[date] = {
            'type': 'Rest Day' if is_rest_day else 'Workout Day',
            'schedule': create_day_schedule(
                user_data,
                collections,
                is_rest_day,
                date
            )
        }

    return schedule


def get_day_type(day_index: int, goals: List[str]) -> str:
    """
    Return a default day type based on day index and goals.

    Args:
        day_index: Index of the day in the week
        goals: List of fitness goals

    Returns:
        String indicating the day type
    """
    if 'Muscle Gain' in goals:
        types = ['Push', 'Pull', 'Legs', 'Upper Body', 'Lower Body']
    else:
        types = ['Full Body', 'Cardio', 'Strength', 'HIIT', 'Endurance']

    return types[day_index % len(types)]


def generate_weekly_plan(user_data: Dict, collections: Dict) -> Dict:
    """
    Generate a weekly holistic fitness plan based on user data.

    Args:
        user_data: Dictionary with user preferences
        collections: Dictionary of MongoDB collections

    Returns:
        Complete weekly workout plan as a dictionary
    """
    validate_user_data(user_data)

    # Generate the weekly schedule
    schedule = create_weekly_schedule(user_data, collections)

    return {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'start_date': user_data['start_date'],
            'user_data': {
                'goals': user_data['fitness_goals'],
                'level': user_data['experience_level'],
                'preferred_rest_day': user_data['preferred_rest_day']
            }
        },
        'schedule': schedule
    }


def calculate_bmi(weight: float, height: float) -> float:
    """
    Calculate BMI from weight (kg) and height (cm).

    Args:
        weight: Weight in kilograms
        height: Height in centimeters

    Returns:
        BMI value as a float
    """
    height_m = height / 100
    return weight / (height_m * height_m)


def map_goals_to_valid_tags(goals: list) -> dict:
    """
    Map fitness goals to valid tags for each collection.

    Args:
        goals: List of fitness goals
            Available goals: ["Flexibility", "Better Mental Health", "Stress Resilience",
                            "General Fitness", "Weight Loss", "Muscle Gain"]

    Returns:
        Dictionary mapping collections to lists of relevant tags
    """
    # Define the mappings from goals to tags for each collection
    mapping = {
        "exercises": {
            "Muscle Gain": ["push", "upper-body", "compound", "strength"],
            "Weight Loss": ["hiit", "full-body", "cardio"],
            "General Fitness": ["functional", "bodyweight", "compound", "general"],
            "Flexibility": ["bodyweight", "functional", "mobility"],
            "Better Mental Health": ["bodyweight", "functional"],
            "Stress Resilience": ["functional", "bodyweight"],
        },
        "breathwork": {
            "General Fitness": ["hiit", "recovery", "foam-rolling", "stretching"],
            "Weight Loss": ["hiit", "recovery", "foam-rolling", "stretching"],
            "Better Mental Health": ["recovery", "foam-rolling"],
            "Flexibility": ["recovery", "stretching"],
            "Stress Resilience": ["recovery", "relaxation"],
            "Muscle Gain": ["recovery", "power"],
        },
        "meditation": {
            "Better Mental Health": ["mindfulness", "relaxation", "anxiety-reduction", "awareness"],
            "Stress Resilience": ["relaxation", "anxiety-reduction", "awareness"],
            "General Fitness": ["mindfulness", "relaxation"],
            "Flexibility": ["mindfulness", "body-awareness"],
            "Weight Loss": ["focus", "discipline"],
            "Muscle Gain": ["focus", "visualization"],
        },
        "stretching": {
            "Flexibility": ["morning", "mobility", "wake-up", "energizing"],
            "General Fitness": ["mobility", "functional"],
            "Weight Loss": ["full-body", "active"],
            "Better Mental Health": ["relaxation", "mindful"],
            "Stress Resilience": ["relaxation", "recovery"],
            "Muscle Gain": ["recovery", "muscle-specific"],
        },
        "cool_downs": {
            "General Fitness": ["general", "basic", "relaxation", "recovery"],
            "Weight Loss": ["general", "basic", "relaxation", "recovery"],
            "Flexibility": ["stretching", "mobility"],
            "Better Mental Health": ["relaxation", "mindful"],
            "Stress Resilience": ["relaxation", "recovery"],
            "Muscle Gain": ["recovery", "gentle"],
        },
        "warm_ups": {
            "General Fitness": ["general", "foundational", "no-equipment", "scalable"],
            "Muscle Gain": ["strength", "activation", "mobility", "preparation"],
            "Weight Loss": ["cardio", "full-body", "hiit"],
            "Flexibility": ["mobility", "dynamic"],
            "Better Mental Health": ["energizing", "focus"],
            "Stress Resilience": ["grounding", "energizing"],
        }
    }

    # Define default tags for each collection as a fallback
    DEFAULT_TAGS = {
        "exercises": ["functional", "bodyweight", "compound", "general"],
        "breathwork": ["recovery", "relaxation"],
        "meditation": ["mindfulness", "relaxation"],
        "stretching": ["general", "full-body"],
        "cool_downs": ["general", "basic"],
        "warm_ups": ["general", "foundational"]
    }

    # Build the result dictionary
    result = {}
    for collection, goal_map in mapping.items():
        tags = []
        for goal in goals:
            if goal in goal_map:
                tags.extend(goal_map[goal])
            else:
                # Add default tags if no mapping for this goal
                tags.extend(DEFAULT_TAGS.get(collection, []))

        # If empty, use defaults
        if not tags and collection in DEFAULT_TAGS:
            tags = DEFAULT_TAGS[collection]

        result[collection] = list(set(tags)) if tags else []

    return result


# Shared helper function for fetch operations
def execute_query_with_fallbacks(collection, queries, limit=5):
    """
    Execute a series of MongoDB queries, falling back to the next if no results.

    Args:
        collection: MongoDB collection to query
        queries: List of queries to try in order
        limit: Maximum number of results to return

    Returns:
        List of documents matching the first successful query
    """
    for query in queries:
        results = list(collection.find(query).limit(limit))
        if results:
            return results

    # Last resort - get any documents
    return list(collection.find().limit(limit))


def fetch_exercises(user_data: dict, collections: dict, day_date: str = None) -> list:
    """
    Fetch exercises from the 'exercises' collection, filtered by user's fitness goals.

    Args:
        user_data: Dictionary with user preferences
        collections: Dictionary of MongoDB collections
        day_date: Date string for consistent randomization

    Returns:
        List of exercise documents
    """
    mapping = map_goals_to_valid_tags(user_data['fitness_goals'])
    valid_tags = mapping.get("exercises", [])
    level = user_data['experience_level']

    # Build queries with fallbacks
    queries = [
        # Try with specific difficulty level first
        {'tags': {'$in': valid_tags}, f'difficulty_levels.{level}': {'$exists': True}},

        # Fallback to intermediate if advanced
        {'tags': {'$in': valid_tags}, 'difficulty_levels.intermediate': {'$exists': True}}
        if level == 'advanced' else None,

        # Fallback to beginner if advanced/intermediate
        {'tags': {'$in': valid_tags}, 'difficulty_levels.beginner': {'$exists': True}}
        if level in ['advanced', 'intermediate'] else None,

        # Try without tag filtering
        {f'difficulty_levels.{level}': {'$exists': True}}
    ]

    # Remove None queries
    queries = [q for q in queries if q is not None]

    exercises = execute_query_with_fallbacks(collections['exercises'], queries)

    if not exercises:
        return []

    # Create day-based randomization for variety
    if day_date:
        # Use day date to seed random for consistent but varied results
        random.seed(f"{day_date}_{user_data['experience_level']}")

    # Return random selection of exercises
    random_selection = random.sample(exercises, min(5, len(exercises)))

    # Reset random seed
    random.seed()

    return random_selection


def fetch_breathwork(level: str, collections: Dict, day_date: str = None) -> List[Dict]:
    """
    Fetch breathwork techniques based on difficulty level.

    Args:
        level: User's experience level
        collections: Dictionary of MongoDB collections
        day_date: Date string for cache key and randomization

    Returns:
        List of breathwork documents
    """
    # Include day in cache key for variety across days
    cache_key = f"breathwork_{level}_{day_date}" if day_date else f"breathwork_{level}"

    if cache_key in template_cache:
        return template_cache[cache_key]

    # Build queries with fallbacks
    queries = [
        # Try with exact level first
        {'difficulty': level, 'recommended_use.pre_workout': True},

        # Fallback to intermediate if advanced
        {'difficulty': 'intermediate', 'recommended_use.pre_workout': True}
        if level == 'advanced' else None,

        # Fallback to beginner if advanced/intermediate
        {'difficulty': 'beginner', 'recommended_use.pre_workout': True}
        if level in ['advanced', 'intermediate'] else None,

        # Try without pre_workout filter
        {'difficulty': {'$in': ['beginner', 'intermediate', 'advanced']}}
    ]

    # Remove None queries
    queries = [q for q in queries if q is not None]

    techniques = execute_query_with_fallbacks(collections['breathwork'], queries, 3)

    template_cache[cache_key] = techniques
    return techniques


def fetch_meditations(level: str, collections: Dict, day_date: str = None) -> List[Dict]:
    """
    Fetch meditation templates based on difficulty level.

    Args:
        level: User's experience level
        collections: Dictionary of MongoDB collections
        day_date: Date string for cache key and randomization

    Returns:
        List of meditation documents
    """
    # Include day in cache key for variety across days
    cache_key = f"meditation_{level}_{day_date}" if day_date else f"meditation_{level}"

    if cache_key in template_cache:
        return template_cache[cache_key]

    # Build queries with fallbacks
    queries = [
        # Try with exact level first
        {'difficulty': level, 'duration_minutes.short': {'$lte': 15}},

        # Fallback to intermediate if advanced
        {'difficulty': 'intermediate', 'duration_minutes.short': {'$lte': 15}}
        if level == 'advanced' else None,

        # Fallback to beginner if advanced/intermediate
        {'difficulty': 'beginner', 'duration_minutes.short': {'$lte': 15}}
        if level in ['advanced', 'intermediate'] else None,

        # Try without duration filter
        {'difficulty': {'$in': ['beginner', 'intermediate', 'advanced']}}
    ]

    # Remove None queries
    queries = [q for q in queries if q is not None]

    meditations = execute_query_with_fallbacks(collections['meditation'], queries, 3)

    template_cache[cache_key] = meditations
    return meditations


def fetch_stretching(user_data: Dict, collections: Dict, day_date: str = None) -> List[Dict]:
    """
    Fetch stretching routines based on user data.

    Args:
        user_data: Dictionary with user preferences
        collections: Dictionary of MongoDB collections
        day_date: Date string for cache key and randomization

    Returns:
        List of stretching documents
    """
    level = user_data['experience_level']

    # Include day in cache key for variety across days
    cache_key = (f"stretching_{level}_{'-'.join(sorted(user_data['fitness_goals']))}_{day_date}"
                 if day_date else f"stretching_{level}_{'-'.join(sorted(user_data['fitness_goals']))}")

    if cache_key in template_cache:
        return template_cache[cache_key]

    # Get tags from goals
    tags = map_goals_to_valid_tags(user_data['fitness_goals']).get("stretching", [])

    # Build queries with fallbacks
    queries = [
        # Try with exact level and tags first
        {'difficulty': level, 'tags': {'$in': tags}},

        # Try with just the level
        {'difficulty': level},

        # Fallback to intermediate if advanced
        {'difficulty': 'intermediate'}
        if level == 'advanced' else None,

        # Fallback to beginner if advanced/intermediate
        {'difficulty': 'beginner'}
        if level in ['advanced', 'intermediate'] else None
    ]

    # Remove None queries
    queries = [q for q in queries if q is not None]

    routines = execute_query_with_fallbacks(collections['stretching'], queries, 3)

    template_cache[cache_key] = routines
    return routines


def fetch_routine_by_level_and_tags(collection_name: str, user_data: Dict,
                                    collections: Dict, day_date: str = None,
                                    limit: int = 3) -> List[Dict]:
    """
    Generic function to fetch routines from collections based on user level and tags.

    Args:
        collection_name: Name of the collection to fetch from ('warm_ups', 'cool_downs', etc.)
        user_data: Dictionary with user preferences
        collections: Dictionary of MongoDB collections
        day_date: Date string for cache key and randomization
        limit: Maximum number of items to return

    Returns:
        List of matching documents from the specified collection
    """
    level = user_data['experience_level']

    # Include day in cache key for variety across days
    sorted_goals = '-'.join(sorted(user_data.get('fitness_goals', [])))
    cache_key = (f"{collection_name}_{level}_{sorted_goals}_{day_date}"
                 if day_date else f"{collection_name}_{level}_{sorted_goals}")

    if cache_key in template_cache:
        return template_cache[cache_key]

    # Get tags from goals
    tags = map_goals_to_valid_tags(user_data.get('fitness_goals', [])).get(collection_name, [])

    # Build queries with fallbacks
    queries = [
        # Try with tags and difficulty level first
        {'tags': {'$in': tags}, f'difficulty_levels.{level}': {'$exists': True}},

        # Try with just the tags
        {'tags': {'$in': tags}},

        # Try with just the difficulty level
        {f'difficulty_levels.{level}': {'$exists': True}},

        # Fallback to intermediate if advanced
        {'difficulty_levels.intermediate': {'$exists': True}}
        if level == 'advanced' else None,

        # Fallback to beginner if advanced/intermediate
        {'difficulty_levels.beginner': {'$exists': True}}
        if level in ['advanced', 'intermediate'] else None
    ]

    # Remove None queries
    queries = [q for q in queries if q is not None]

    results = execute_query_with_fallbacks(collections[collection_name], queries, limit)

    template_cache[cache_key] = results
    return results


def fetch_warm_ups(user_data: Dict, collections: Dict, day_date: str = None) -> List[Dict]:
    """
    Fetch warm-up routines based on user data.

    Args:
        user_data: Dictionary with user preferences
        collections: Dictionary of MongoDB collections
        day_date: Date string for cache key and randomization

    Returns:
        List of warm-up documents
    """
    return fetch_routine_by_level_and_tags('warm_ups', user_data, collections, day_date)


def fetch_cool_downs(user_data: Dict, collections: Dict, day_date: str = None) -> List[Dict]:
    """
    Fetch cool-down routines based on user data.

    Args:
        user_data: Dictionary with user preferences
        collections: Dictionary of MongoDB collections
        day_date: Date string for cache key and randomization

    Returns:
        List of cool-down documents
    """
    return fetch_routine_by_level_and_tags('cool_downs', user_data, collections, day_date)


def prioritize_exercises(exercises: List[Dict], goals: List[str]) -> List[Dict]:
    """
    Randomly select and prioritize a balanced set of exercises.

    Args:
        exercises: List of exercise documents
        goals: List of fitness goals

    Returns:
        Prioritized list of exercises
    """
    selected = []
    exercise_types = set()

    for ex in sorted(exercises, key=lambda _: random.random()):
        ex_type = next((tag for tag in ex['tags'] if tag in ['push', 'pull', 'legs', 'core']), None)
        if len(selected) < 5 and (not ex_type or ex_type not in exercise_types):
            selected.append(ex)
            if ex_type:
                exercise_types.add(ex_type)

    return selected[:5]
