import random
from datetime import datetime, timedelta
from typing import Dict, List

# Global caches to avoid re-fetching data (optional)
exercise_cache = {}
template_cache = {}


def validate_user_data(user_data: Dict) -> None:
    """Validate required user data fields."""
    required_fields = [
        'weight', 'height', 'fitness_goals', 'experience_level',
        'preferred_rest_day', 'workout_duration', 'start_date', 'date_range'
    ]
    missing_fields = [field for field in required_fields if field not in user_data]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    if not isinstance(user_data['fitness_goals'], list):
        raise ValueError("fitness_goals must be a list")

    valid_levels = ['beginner', 'intermediate', 'advanced']
    if user_data['experience_level'] not in valid_levels:
        raise ValueError(f"experience_level must be one of: {', '.join(valid_levels)}")

    valid_workout_durations = [15, 30, 45, 60]
    if user_data['workout_duration'] not in valid_workout_durations:
        raise ValueError(f"workout_duration must be one of: {valid_workout_durations}")

    # Validate date_range
    if not isinstance(user_data['date_range'], list) or len(user_data['date_range']) != 7:
        raise ValueError("date_range must be a list of 7 date strings")


def add_minutes(time, minutes):
    """Add minutes to a datetime object."""
    return time + timedelta(minutes=minutes)


def create_day_schedule(user_data: Dict, collections: Dict, is_rest_day: bool, day_date: str) -> List[Dict]:
    """Create a daily schedule by combining items from multiple collections."""
    if is_rest_day:
        return []

    daily_schedule = []
    total_workout_time = user_data.get('workout_duration', 30)  # Default to 30 minutes

    # Create empty schedule to fill in proper order
    schedule_template = {
        'warm_up': None,
        'breathwork': None,
        'main_exercises': [],
        'stretching': None,
        'cool_down': None,
        'meditation': None
    }

    # Adjust durations based on total workout time
    # For shorter workouts, we need to make components more compact
    if total_workout_time <= 15:
        warmup_time = 4
        breathwork_time = 0  # No breathwork for 15-minute workouts
        cooldown_time = 4
        meditation_time = 3
        stretching_time = 0  # No stretching for 15-minute workouts
        max_exercises = 2  # Increased to 2 exercises
        include_stretching = False
        include_breathwork = False
    elif total_workout_time <= 30:
        warmup_time = 5
        breathwork_time = 3
        cooldown_time = 5
        meditation_time = 5
        stretching_time = 0  # No stretching for 30-minute workouts
        max_exercises = 2
        include_stretching = False
        include_breathwork = True
    elif total_workout_time <= 45:  # 45 minutes
        warmup_time = 5
        breathwork_time = 5
        cooldown_time = 5
        meditation_time = 5
        stretching_time = 0  # No stretching for 45-minute workouts either
        max_exercises = 4  # Increased exercises instead of stretching
        include_stretching = False
        include_breathwork = True
    else:  # 60 minutes
        warmup_time = 7
        breathwork_time = 5
        cooldown_time = 7
        meditation_time = 7
        stretching_time = 10
        max_exercises = 4
        include_stretching = True
        include_breathwork = True

    # Use day_date as seed for selections
    day_seed_base = sum(ord(c) for c in day_date)

    # 1. Fetch Warm-Up - ensure variety by using day-based selection
    warmups = fetch_warm_ups(user_data, collections, day_date)
    if warmups and len(warmups) > 0:
        # Use the day date as a seed for consistent but varied selection
        random.seed(day_seed_base)
        warmup = random.choice(warmups)
        random.seed()  # Reset random seed

        schedule_template['warm_up'] = {
            'activity': {
                '_id': warmup.get('_id'),
                'name': warmup.get('name', 'Warm-Up'),
                'phases': warmup.get('phases', []),  # Include full phases structure
                'instructions': warmup.get('instructions', []),
                'benefits': warmup.get('benefits', []),
                'target_areas': warmup.get('target_areas', []),
                'type': 'warm_up',
                'equipment_needed': warmup.get('equipment_needed', 'None'),
                'target_heart_rate': warmup.get('target_heart_rate', '')
            },
            'duration': warmup_time
        }

    # 2. Fetch Breathwork - ensure variety by using day-based selection
    if include_breathwork:
        breathwork = fetch_breathwork(user_data['experience_level'], collections, day_date)
        if breathwork and len(breathwork) > 0:
            # Use the day date as a seed for consistent but varied selection
            random.seed(day_seed_base + 1)  # Add 1 to make it different from warmup seed
            breath = random.choice(breathwork)
            random.seed()  # Reset random seed

            schedule_template['breathwork'] = {
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

    # 3. Fetch Main Exercises - ensure variety using day-based selection
    main_exercises = fetch_exercises(user_data, collections, day_date)
    # Calculate remaining time for main exercises after warm-up, breathwork
    auxiliary_time = (warmup_time if schedule_template['warm_up'] else 0) + \
                     (breathwork_time if schedule_template['breathwork'] else 0) + \
                     cooldown_time + meditation_time + \
                     (stretching_time if include_stretching else 0)
    remaining_time = total_workout_time - auxiliary_time

    # Limit number of exercises based on available time
    exercise_count = min(len(main_exercises), max_exercises)
    if exercise_count > 0:
        time_per_exercise = max(5, remaining_time // exercise_count)
        for ex in main_exercises[:exercise_count]:
            difficulty_level = user_data['experience_level']
            # If the specific difficulty level isn't available, try to fall back
            if difficulty_level not in ex.get('difficulty_levels', {}):
                if 'intermediate' in ex.get('difficulty_levels', {}) and difficulty_level == 'advanced':
                    difficulty_level = 'intermediate'
                elif 'beginner' in ex.get('difficulty_levels', {}):
                    difficulty_level = 'beginner'
                else:
                    difficulty_level = next(iter(ex.get('difficulty_levels', {}).keys()), None)

            if difficulty_level:
                schedule_template['main_exercises'].append({
                    'activity': {
                        '_id': ex.get('_id'),
                        'name': ex.get('name', 'Unnamed Exercise'),
                        'exercises': [{
                            'name': ex.get('name', 'Unnamed Exercise'),
                            'form_cues': ex.get('form_cues', []),
                            'sets': ex['difficulty_levels'][difficulty_level].get('sets', 'N/A'),
                            'reps': ex['difficulty_levels'][difficulty_level].get('reps', 'N/A'),
                            'target_muscles': ex.get('target_muscles', [])
                        }],
                        'type': 'exercise'
                    },
                    'duration': time_per_exercise
                })

    # 4. Fetch Stretching - only for longer workouts
    if include_stretching:
        stretching = fetch_stretching(user_data, collections, day_date)
        if stretching and len(stretching) > 0:
            # Use the day date as a seed for consistent but varied selection
            random.seed(day_seed_base + 2)  # Add 2 to make it different
            stretch = random.choice(stretching)
            random.seed()  # Reset random seed

            schedule_template['stretching'] = {
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

    # 5. Fetch Cool-down - ensure variety by using day-based selection
    cooldowns = fetch_cool_downs(user_data, collections, day_date)
    if cooldowns and len(cooldowns) > 0:
        # Use the day date as a seed for consistent but varied selection
        random.seed(day_seed_base + 3)  # Add 3 to make it different
        cooldown = random.choice(cooldowns)
        random.seed()  # Reset random seed

        schedule_template['cool_down'] = {
            'activity': {
                '_id': cooldown.get('_id'),
                'name': cooldown.get('name', 'Cool-Down'),
                'phases': cooldown.get('phases', []),  # Include full phases structure
                'instructions': cooldown.get('instructions', []),
                'benefits': cooldown.get('benefits', []),
                'target_areas': cooldown.get('target_areas', []),
                'type': 'cool_down',
                'equipment_needed': cooldown.get('equipment_needed', 'None'),
                'target_heart_rate': cooldown.get('target_heart_rate', '')
            },
            'duration': cooldown_time
        }

    # 6. Fetch Meditation - ensure variety by using day-based selection
    meditations = fetch_meditations(user_data['experience_level'], collections, day_date)
    if meditations and len(meditations) > 0:
        # Use the day date as a seed for consistent but varied selection
        random.seed(day_seed_base + 4)  # Add 4 to make it different
        meditation = random.choice(meditations)
        random.seed()  # Reset random seed

        duration = meditation.get('duration_minutes', {})
        if isinstance(duration, dict):
            duration = duration.get('short', 10)
        schedule_template['meditation'] = {
            'activity': {
                '_id': meditation.get('_id'),
                'name': meditation.get('name', 'Meditation'),
                'steps': meditation.get('steps', []),
                'benefits': meditation.get('benefits', []),
                'type': 'meditation'
            },
            'duration': meditation_time
        }

    # Build final schedule in correct order
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
    """Create a weekly schedule based on user data and valid items from local DB."""
    date_range = user_data.get('date_range', [])
    schedule = {}

    # Get preferred rest day from user data
    preferred_rest_day = user_data.get('preferred_rest_day')

    for i, date in enumerate(date_range):
        if date == preferred_rest_day:
            schedule[date] = {
                'type': 'Rest Day',
                'schedule': []
            }
        else:
            # Create daily schedule for this date
            daily_schedule = create_day_schedule(
                user_data,
                collections,
                is_rest_day=(date == preferred_rest_day),
                day_date=date
            )
            schedule[date] = {
                'type': 'Workout Day',
                'schedule': daily_schedule
            }

    return schedule


def get_day_type(day_index: int, goals: List[str]) -> str:
    """Return a default day type based on day index and goals."""
    if 'Muscle Gain' in goals:
        types = ['Push', 'Pull', 'Legs', 'Upper Body', 'Lower Body']
    else:
        types = ['Full Body', 'Cardio', 'Strength', 'HIIT', 'Endurance']
    return types[day_index % len(types)]


def generate_weekly_plan(user_data: Dict, collections: Dict) -> Dict:
    """Generate a weekly holistic fitness plan."""
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
    """Calculate BMI from weight (kg) and height (cm)."""
    height_m = height / 100
    return weight / (height_m * height_m)


def map_goals_to_valid_tags(goals: list) -> dict:
    """
    Map fitness goals to valid tags for each collection.

    Available fitness goals:
      ["Flexibility", "Better Mental Health", "Stress Resilience", "General Fitness", "Weight Loss", "Muscle Gain"]
    """
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

    # Every collection should have a fallback for all goals
    DEFAULT_TAGS = {
        "exercises": ["functional", "bodyweight", "compound", "general"],
        "breathwork": ["recovery", "relaxation"],
        "meditation": ["mindfulness", "relaxation"],
        "stretching": ["general", "full-body"],
        "cool_downs": ["general", "basic"],
        "warm_ups": ["general", "foundational"]
    }

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


# Fetch functions for each collection

def fetch_exercises(user_data: dict, collections: dict, day_date: str = None) -> list:
    """
    Fetch exercises from the 'exercises' collection,
    filtered by valid tags derived from the user's fitness goals.
    """
    mapping = map_goals_to_valid_tags(user_data['fitness_goals'])
    valid_tags = mapping.get("exercises", [])
    level = user_data['experience_level']

    # Try with specific difficulty level first
    query = {
        'tags': {'$in': valid_tags},
        f'difficulty_levels.{level}': {'$exists': True}
    }
    exercises = list(collections['exercises'].find(query))

    # If no exercises found, try fallback to other levels
    if not exercises and level == 'advanced':
        query = {
            'tags': {'$in': valid_tags},
            'difficulty_levels.intermediate': {'$exists': True}
        }
        exercises = list(collections['exercises'].find(query))

    if not exercises and (level == 'advanced' or level == 'intermediate'):
        query = {
            'tags': {'$in': valid_tags},
            'difficulty_levels.beginner': {'$exists': True}
        }
        exercises = list(collections['exercises'].find(query))

    # If still no exercises, try without tag filtering
    if not exercises:
        query = {f'difficulty_levels.{level}': {'$exists': True}}
        exercises = list(collections['exercises'].find(query))

    # Last resort - get any exercises
    if not exercises:
        exercises = list(collections['exercises'].find().limit(5))

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
    """Fetch breathwork techniques based on level."""
    # Include day in cache key for variety across days
    cache_key = f"breathwork_{level}_{day_date}" if day_date else f"breathwork_{level}"

    if cache_key in template_cache:
        return template_cache[cache_key]

    # Try with exact level first
    query = {'difficulty': level, 'recommended_use.pre_workout': True}
    techniques = list(collections['breathwork'].find(query))

    # If no results for advanced, try intermediate
    if not techniques and level == 'advanced':
        query = {'difficulty': 'intermediate', 'recommended_use.pre_workout': True}
        techniques = list(collections['breathwork'].find(query))

    # If still no results, try beginner
    if not techniques and (level == 'advanced' or level == 'intermediate'):
        query = {'difficulty': 'beginner', 'recommended_use.pre_workout': True}
        techniques = list(collections['breathwork'].find(query))

    # If still nothing, try without pre_workout filter
    if not techniques:
        query = {'difficulty': {'$in': ['beginner', 'intermediate', 'advanced']}}
        techniques = list(collections['breathwork'].find(query))

    # If still nothing, get anything
    if not techniques:
        techniques = list(collections['breathwork'].find().limit(3))

    template_cache[cache_key] = techniques
    return techniques


def fetch_meditations(level: str, collections: Dict, day_date: str = None) -> List[Dict]:
    """Fetch meditation templates based on level."""
    # Include day in cache key for variety across days
    cache_key = f"meditation_{level}_{day_date}" if day_date else f"meditation_{level}"

    if cache_key in template_cache:
        return template_cache[cache_key]

    # Try with exact level first
    query = {'difficulty': level, 'duration_minutes.short': {'$lte': 15}}
    meditations = list(collections['meditation'].find(query))

    # If no results for advanced, try intermediate
    if not meditations and level == 'advanced':
        query = {'difficulty': 'intermediate', 'duration_minutes.short': {'$lte': 15}}
        meditations = list(collections['meditation'].find(query))

    # If still no results, try beginner
    if not meditations and (level == 'advanced' or level == 'intermediate'):
        query = {'difficulty': 'beginner', 'duration_minutes.short': {'$lte': 15}}
        meditations = list(collections['meditation'].find(query))

    # If still nothing, try without duration filter
    if not meditations:
        query = {'difficulty': {'$in': ['beginner', 'intermediate', 'advanced']}}
        meditations = list(collections['meditation'].find(query))

    # If still nothing, get anything
    if not meditations:
        meditations = list(collections['meditation'].find().limit(3))

    template_cache[cache_key] = meditations
    return meditations


def fetch_stretching(user_data: Dict, collections: Dict, day_date: str = None) -> List[Dict]:
    """Fetch stretching routines based on user data."""
    level = user_data['experience_level']

    # Include day in cache key for variety across days
    cache_key = (f"stretching_{level}_{'-'.join(sorted(user_data['fitness_goals']))}_{day_date}"
                 if day_date else f"stretching_{level}_{'-'.join(sorted(user_data['fitness_goals']))}")

    if cache_key in template_cache:
        return template_cache[cache_key]

    # Get tags from goals
    tags = map_goals_to_valid_tags(user_data['fitness_goals']).get("stretching", [])

    # Try with exact level and tags first
    query = {'difficulty': level, 'tags': {'$in': tags}}
    routines = list(collections['stretching'].find(query))

    # If no results, try with just the level
    if not routines:
        query = {'difficulty': level}
        routines = list(collections['stretching'].find(query))

    # If still no results and level is advanced, try intermediate
    if not routines and level == 'advanced':
        query = {'difficulty': 'intermediate'}
        routines = list(collections['stretching'].find(query))

    # If still no results, try beginner
    if not routines and (level == 'advanced' or level == 'intermediate'):
        query = {'difficulty': 'beginner'}
        routines = list(collections['stretching'].find(query))

    # Last resort - get any stretching routines
    if not routines:
        routines = list(collections['stretching'].find().limit(3))

    template_cache[cache_key] = routines
    return routines


def fetch_warm_ups(user_data: Dict, collections: Dict, day_date: str = None) -> List[Dict]:
    """Fetch warm-up routines based on user data."""
    level = user_data['experience_level']

    # Include day in cache key for variety across days
    cache_key = (f"warm_ups_{level}_{'-'.join(sorted(user_data['fitness_goals']))}_{day_date}"
                 if day_date else f"warm_ups_{level}_{'-'.join(sorted(user_data['fitness_goals']))}")

    if cache_key in template_cache:
        return template_cache[cache_key]

    # Get tags from goals
    tags = map_goals_to_valid_tags(user_data['fitness_goals']).get("warm_ups", [])

    # Try with tags and difficulty level first
    query = {
        'tags': {'$in': tags},
        f'difficulty_levels.{level}': {'$exists': True}
    }
    warmups = list(collections['warm_ups'].find(query))

    # If no results, try with just the tags
    if not warmups:
        query = {'tags': {'$in': tags}}
        warmups = list(collections['warm_ups'].find(query))

    # If still no results, try with just the difficulty level
    if not warmups:
        query = {f'difficulty_levels.{level}': {'$exists': True}}
        warmups = list(collections['warm_ups'].find(query))

    # If still no results for advanced, try intermediate
    if not warmups and level == 'advanced':
        query = {'difficulty_levels.intermediate': {'$exists': True}}
        warmups = list(collections['warm_ups'].find(query))

    # If still no results, try beginner
    if not warmups and (level == 'advanced' or level == 'intermediate'):
        query = {'difficulty_levels.beginner': {'$exists': True}}
        warmups = list(collections['warm_ups'].find(query))

    # Last resort - get any warm-ups
    if not warmups:
        warmups = list(collections['warm_ups'].find().limit(3))

    template_cache[cache_key] = warmups
    return warmups


def fetch_cool_downs(user_data: Dict, collections: Dict, day_date: str = None) -> List[Dict]:
    """Fetch cool-down routines based on user data."""
    level = user_data['experience_level']

    # Include day in cache key for variety across days
    cache_key = (f"cool_downs_{level}_{'-'.join(sorted(user_data['fitness_goals']))}_{day_date}"
                 if day_date else f"cool_downs_{level}_{'-'.join(sorted(user_data['fitness_goals']))}")

    if cache_key in template_cache:
        return template_cache[cache_key]

    # Get tags from goals
    tags = map_goals_to_valid_tags(user_data['fitness_goals']).get("cool_downs", [])

    # Try with tags and difficulty level first
    query = {
        'tags': {'$in': tags},
        f'difficulty_levels.{level}': {'$exists': True}
    }
    cooldowns = list(collections['cool_downs'].find(query))

    # If no results, try with just the tags
    if not cooldowns:
        query = {'tags': {'$in': tags}}
        cooldowns = list(collections['cool_downs'].find(query))

    # If still no results, try with just the difficulty level
    if not cooldowns:
        query = {f'difficulty_levels.{level}': {'$exists': True}}
        cooldowns = list(collections['cool_downs'].find(query))

    # If still no results for advanced, try intermediate
    if not cooldowns and level == 'advanced':
        query = {'difficulty_levels.intermediate': {'$exists': True}}
        cooldowns = list(collections['cool_downs'].find(query))

    # If still no results, try beginner
    if not cooldowns and (level == 'advanced' or level == 'intermediate'):
        query = {'difficulty_levels.beginner': {'$exists': True}}
        cooldowns = list(collections['cool_downs'].find(query))

    # Last resort - get any cool-downs
    if not cooldowns:
        cooldowns = list(collections['cool_downs'].find().limit(3))

    template_cache[cache_key] = cooldowns
    return cooldowns


def prioritize_exercises(exercises: List[Dict], goals: List[str]) -> List[Dict]:
    """Randomly select and prioritize a balanced set of exercises."""
    selected = []
    exercise_types = set()
    for ex in sorted(exercises, key=lambda _: random.random()):
        ex_type = next((tag for tag in ex['tags'] if tag in ['push', 'pull', 'legs', 'core']), None)
        if len(selected) < 5 and (not ex_type or ex_type not in exercise_types):
            selected.append(ex)
            if ex_type:
                exercise_types.add(ex_type)
    return selected[:5]
