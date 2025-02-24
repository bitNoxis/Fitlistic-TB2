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
        'preferred_rest_day', 'workout_duration'
    ]
    missing_fields = [field for field in required_fields if field not in user_data]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    if not isinstance(user_data['fitness_goals'], list):
        raise ValueError("fitness_goals must be a list")

    valid_levels = ['beginner', 'intermediate', 'advanced']
    if user_data['experience_level'] not in valid_levels:
        raise ValueError(f"experience_level must be one of: {', '.join(valid_levels)}")

    valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    if user_data['preferred_rest_day'].lower() not in valid_days:
        raise ValueError(f"preferred_rest_day must be one of: {', '.join(valid_days)}")

    valid_workout_durations = [30, 45, 60, 90]
    if user_data['workout_duration'] not in valid_workout_durations:
        raise ValueError(f"workout_duration must be one of: {valid_workout_durations}")


def add_minutes(time, minutes):
    """Add minutes to a datetime object."""
    return time + timedelta(minutes=minutes)


def create_day_schedule(user_data: Dict, collections: Dict, is_rest_day: bool) -> List[Dict]:
    """Create a daily schedule by combining items from multiple collections."""
    if is_rest_day:
        return []

    daily_schedule = []
    total_workout_time = user_data.get('workout_duration', 60)

    # Create empty schedule to fill in proper order
    schedule_template = {
        'warm_up': None,
        'breathwork': None,
        'main_exercises': [],
        'stretching': None,
        'cool_down': None,
        'meditation': None
    }

    # 1. Fetch Warm-Up
    warmups = fetch_warm_ups(user_data, collections)
    if warmups and len(warmups) > 0:
        warmup = warmups[0]
        schedule_template['warm_up'] = {
            'activity': {
                '_id': warmup.get('_id'),
                'name': warmup.get('name', 'Warm-Up'),
                'sequence': warmup.get('sequence', []),
                'instructions': warmup.get('instructions', []),
                'benefits': warmup.get('benefits', []),
                'target_areas': warmup.get('target_areas', []),
                'type': 'warm_up'
            },
            'duration': 5
        }

    # 2. Fetch Breathwork
    breathwork = fetch_breathwork(user_data['experience_level'], collections)
    if breathwork and len(breathwork) > 0:
        breath = breathwork[0]
        schedule_template['breathwork'] = {
            'activity': {
                '_id': breath.get('_id'),
                'name': breath.get('name', 'Breathwork'),
                'steps': breath.get('steps', []),
                'instructions': breath.get('instructions', []),
                'benefits': breath.get('benefits', []),
                'type': 'breathwork'
            },
            'duration': 5
        }

    # 3. Fetch Main Exercises
    main_exercises = fetch_exercises(user_data, collections)
    exercise_count = min(len(main_exercises), 3)
    if exercise_count > 0:
        time_per_exercise = total_workout_time // exercise_count
        for ex in main_exercises[:exercise_count]:
            schedule_template['main_exercises'].append({
                'activity': {
                    '_id': ex.get('_id'),
                    'name': ex.get('name', 'Unnamed Exercise'),
                    'exercises': [{
                        'name': ex.get('name', 'Unnamed Exercise'),
                        'form_cues': ex.get('form_cues', []),
                        'sets': ex['difficulty_levels'][user_data['experience_level']].get('sets', 'N/A'),
                        'reps': ex['difficulty_levels'][user_data['experience_level']].get('reps', 'N/A'),
                        'target_muscles': ex.get('target_muscles', [])
                    }],
                    'type': 'exercise'
                },
                'duration': time_per_exercise
            })

    # 4. Fetch Stretching
    stretching = fetch_stretching(user_data, collections)
    if stretching and len(stretching) > 0:
        stretch = stretching[0]
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
            'duration': 10
        }

    # 5. Fetch Cool-down
    cooldowns = fetch_cool_downs(user_data, collections)
    if cooldowns and len(cooldowns) > 0:
        cooldown = cooldowns[0]
        schedule_template['cool_down'] = {
            'activity': {
                '_id': cooldown.get('_id'),
                'name': cooldown.get('name', 'Cool-Down'),
                'sequence': cooldown.get('sequence', []),
                'instructions': cooldown.get('instructions', []),
                'benefits': cooldown.get('benefits', []),
                'target_areas': cooldown.get('target_areas', []),
                'type': 'cool_down'
            },
            'duration': 5
        }

    # 6. Fetch Meditation
    meditations = fetch_meditations(user_data['experience_level'], collections)
    if meditations and len(meditations) > 0:
        meditation = meditations[0]
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
            'duration': duration
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
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    schedule = {}

    # Get preferred rest day from user data (defaulting to sunday if not specified)
    preferred_rest_day = user_data.get('preferred_rest_day', 'sunday').lower()

    for i, day in enumerate(days):
        if day == preferred_rest_day:
            schedule[day] = {
                'type': 'Rest & Rejuvenation',
                'schedule': []
            }
        else:
            day_type = get_day_type(i, user_data['fitness_goals'])
            daily_schedule = create_day_schedule(user_data, collections, is_rest_day=(day == preferred_rest_day))
            schedule[day] = {
                'type': day_type,
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

    Example mapping:
      - For "exercises" (general strength exercises):
            For Muscle Gain: ["push", "upper-body", "compound", "strength"]
            For Weight Loss: ["hiit", "full-body", "cardio"]
            For General Fitness: ["functional", "bodyweight", "compound", "general"]
      - For "breathwork": use tags like ["hiit", "recovery", "foam-rolling", "stretching"]
      - For "meditation": use tags like ["mindfulness", "relaxation", "anxiety-reduction", "awareness"]
      - For "stretching": use tags like ["morning", "mobility", "wake-up", "energizing"]
      - For "cool_downs": use tags like ["general", "basic", "relaxation", "recovery"]
      - For "warm_ups": use tags like ["general", "foundational", "no-equipment", "scalable"]

    Returns a dictionary keyed by collection name.
    """
    mapping = {
        "exercises": {
            "Muscle Gain": ["push", "upper-body", "compound", "strength"],
            "Weight Loss": ["hiit", "full-body", "cardio"],
            "General Fitness": ["functional", "bodyweight", "compound", "general"],
        },
        "breathwork": {
            "General Fitness": ["hiit", "recovery", "foam-rolling", "stretching"],
            "Weight Loss": ["hiit", "recovery", "foam-rolling", "stretching"],
            "Better Mental Health": ["recovery", "foam-rolling"],
        },
        "meditation": {
            "Better Mental Health": ["mindfulness", "relaxation", "anxiety-reduction", "awareness"],
            "Stress Resilience": ["relaxation", "anxiety-reduction", "awareness"],
            "General Fitness": ["mindfulness", "relaxation"],
        },
        "stretching": {
            "Flexibility": ["morning", "mobility", "wake-up", "energizing"],
            "General Fitness": ["mobility", "functional"],
        },
        "cool_downs": {
            "General Fitness": ["general", "basic", "relaxation", "recovery"],
            "Weight Loss": ["general", "basic", "relaxation", "recovery"],
        },
        "warm_ups": {
            "General Fitness": ["general", "foundational", "no-equipment", "scalable"],
            "Muscle Gain": ["strength", "activation", "mobility", "preparation"]
        }
    }
    result = {}
    for collection, goal_map in mapping.items():
        tags = []
        for goal in goals:
            if goal in goal_map:
                tags.extend(goal_map[goal])
        result[collection] = list(set(tags)) if tags else []
    return result


# Fetch functions for each collection

def fetch_exercises(user_data: dict, collections: dict) -> list:
    """
    Fetch exercises from the 'exercises' collection,
    filtered by valid tags derived from the user's fitness goals.
    """
    mapping = map_goals_to_valid_tags(user_data['fitness_goals'])
    valid_tags = mapping.get("exercises", [])
    level = user_data['experience_level']
    query = {
        'tags': {'$in': valid_tags},
        f'difficulty_levels.{level}': {'$exists': True}
    }
    exercises = list(collections['exercises'].find(query))
    if not exercises:
        return []
    return random.sample(exercises, min(5, len(exercises)))


def fetch_breathwork(level: str, collections: Dict) -> List[Dict]:
    """Fetch breathwork techniques based on level."""
    cache_key = f"breathwork_{level}"
    if cache_key in template_cache:
        return template_cache[cache_key]
    query = {'difficulty': level, 'recommended_use.pre_workout': True}
    techniques = list(collections['breathwork'].find(query).limit(3))
    template_cache[cache_key] = techniques
    return techniques


def fetch_meditations(level: str, collections: Dict) -> List[Dict]:
    """Fetch meditation templates based on level."""
    cache_key = f"meditation_{level}"
    if cache_key in template_cache:
        return template_cache[cache_key]
    query = {'difficulty': level, 'duration_minutes.short': {'$lte': 15}}
    meditations = list(collections['meditation'].find(query).limit(3))
    template_cache[cache_key] = meditations
    return meditations


def fetch_stretching(user_data: Dict, collections: Dict) -> List[Dict]:
    """Fetch stretching routines based on user data."""
    cache_key = f"stretching_{user_data['experience_level']}_{'-'.join(sorted(user_data['fitness_goals']))}"
    if cache_key in template_cache:
        return template_cache[cache_key]
    query = {
        'difficulty': user_data['experience_level'],
        'tags': {'$in': map_goals_to_valid_tags(user_data['fitness_goals']).get("stretching", [])}
    }
    routines = list(collections['stretching'].find(query).limit(3))
    template_cache[cache_key] = routines
    return routines


def fetch_warm_ups(user_data: Dict, collections: Dict) -> List[Dict]:
    """Fetch warm-up routines based on user data."""
    cache_key = f"warm_ups_{user_data['experience_level']}_{'-'.join(sorted(user_data['fitness_goals']))}"
    if cache_key in template_cache:
        return template_cache[cache_key]
    query = {
        'tags': {'$in': map_goals_to_valid_tags(user_data['fitness_goals']).get("warm_ups", [])},
        f'difficulty_levels.{user_data["experience_level"]}': {'$exists': True}
    }
    warmups = list(collections['warm_ups'].find(query))
    template_cache[cache_key] = warmups
    return warmups


def fetch_cool_downs(user_data: Dict, collections: Dict) -> List[Dict]:
    """Fetch cool-down routines based on user data."""
    cache_key = f"cool_downs_{user_data['experience_level']}_{'-'.join(sorted(user_data['fitness_goals']))}"
    if cache_key in template_cache:
        return template_cache[cache_key]
    query = {
        'tags': {'$in': map_goals_to_valid_tags(user_data['fitness_goals']).get("cool_downs", [])},
        f'difficulty_levels.{user_data["experience_level"]}': {'$exists': True}
    }
    cooldowns = list(collections['cool_downs'].find(query))
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
