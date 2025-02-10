import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class HolisticPlanGenerator:
    def __init__(self, collections):
        """
        Initialize with MongoDB collections

        Args:
            collections: Dictionary containing MongoDB collection references
        """
        self.collections = collections
        self.exercise_cache = {}
        self.template_cache = {}

    def generateWeeklyPlan(self, user_data: Dict) -> Dict:
        """
        Generate a weekly holistic fitness plan

        Args:
            user_data: Dictionary containing user information and preferences
                Required keys:
                - weight (float): User's weight in kg
                - height (float): User's height in cm
                - fitness_goals (List[str]): List of fitness goals
                - experience_level (str): User's experience level
        """
        try:
            # Validate user data
            self._validate_user_data(user_data)

            # Calculate BMI for exercise selection
            bmi = self._calculate_bmi(user_data['weight'], user_data['height'])
            user_data['bmi'] = bmi

            # Fetch components from MongoDB collections
            exercises = self.fetch_exercises(user_data)
            breathwork = self.fetch_breathwork(user_data['experience_level'])
            meditations = self.fetch_meditations(user_data['experience_level'])
            stretching = self.fetch_stretching(user_data)

            # Generate weekly schedule
            schedule = self.create_weekly_schedule(
                exercises=exercises,
                breathwork=breathwork,
                meditations=meditations,
                stretching=stretching,
                user_data=user_data
            )

            # Add metadata to the plan
            return {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'user_data': {
                        'goals': user_data['fitness_goals'],
                        'level': user_data['experience_level'],
                        'bmi': bmi
                    }
                },
                'schedule': schedule
            }

        except Exception as e:
            raise Exception(f"Error generating plan: {str(e)}")

    def _validate_user_data(self, user_data: Dict) -> None:
        """Validate required user data fields"""
        required_fields = ['weight', 'height', 'fitness_goals', 'experience_level']
        missing_fields = [field for field in required_fields if field not in user_data]

        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        if not isinstance(user_data['fitness_goals'], list):
            raise ValueError("fitness_goals must be a list")

        valid_levels = ['beginner', 'intermediate', 'advanced']
        if user_data['experience_level'] not in valid_levels:
            raise ValueError(f"experience_level must be one of: {', '.join(valid_levels)}")

    def _calculate_bmi(self, weight: float, height: float) -> float:
        """Calculate BMI from weight (kg) and height (cm)"""
        height_m = height / 100
        return weight / (height_m * height_m)

    def fetch_exercises(self, user_data: Dict) -> List[Dict]:
        """Fetch appropriate exercises based on user data"""
        cache_key = f"exercises_{user_data['experience_level']}_{'-'.join(sorted(user_data['fitness_goals']))}"

        if cache_key in self.exercise_cache:
            return self.exercise_cache[cache_key]

        level = user_data['experience_level']
        goals = user_data['fitness_goals']
        exercise_types = self.map_goals_to_types(goals)

        # Build MongoDB query
        query = {
            '$and': [
                {'tags': {'$in': exercise_types}},
                {f'difficulty_levels.{level}': {'$exists': True}},
                # Add BMI-based filters if needed
                {'$or': [
                    {'bmi_restrictions': {'$exists': False}},
                    {'bmi_restrictions.min': {'$lte': user_data['bmi']}},
                    {'bmi_restrictions.max': {'$gte': user_data['bmi']}}
                ]}
            ]
        }

        exercises = list(self.collections['exercises'].find(query))
        prioritized_exercises = self.prioritize_exercises(exercises, goals)

        self.exercise_cache[cache_key] = prioritized_exercises
        return prioritized_exercises

    def fetch_breathwork(self, level: str) -> List[Dict]:
        """Fetch breathing techniques based on level"""
        cache_key = f"breathwork_{level}"

        if cache_key in self.template_cache:
            return self.template_cache[cache_key]

        query = {
            'difficulty': level,
            'recommended_use.pre_workout': True
        }

        techniques = list(self.collections['breathwork'].find(query).limit(3))
        self.template_cache[cache_key] = techniques
        return techniques

    def fetch_meditations(self, level: str) -> List[Dict]:
        """Fetch meditation templates based on level"""
        cache_key = f"meditation_{level}"

        if cache_key in self.template_cache:
            return self.template_cache[cache_key]

        query = {
            'difficulty': level,
            'duration_minutes.short': {'$lte': 15}  # Keep morning meditations short
        }

        meditations = list(self.collections['meditation'].find(query).limit(3))
        self.template_cache[cache_key] = meditations
        return meditations

    def fetch_stretching(self, user_data: Dict) -> List[Dict]:
        """Fetch stretching routines based on user data"""
        cache_key = f"stretching_{user_data['experience_level']}_{'-'.join(sorted(user_data['fitness_goals']))}"

        if cache_key in self.template_cache:
            return self.template_cache[cache_key]

        query = {
            'difficulty': user_data['experience_level'],
            'tags': {'$in': self.map_goals_to_types(user_data['fitness_goals'])}
        }

        routines = list(self.collections['stretching'].find(query).limit(3))
        self.template_cache[cache_key] = routines
        return routines

    def map_goals_to_types(self, goals: List[str]) -> List[str]:
        """Map fitness goals to exercise types"""
        goal_mapping = {
            'Weight Loss': ['cardio', 'hiit', 'fat-burning', 'full-body'],
            'Muscle Gain': ['strength', 'compound', 'muscle-building', 'resistance'],
            'Flexibility': ['flexibility', 'mobility', 'stretching', 'yoga'],
            'Endurance': ['cardio', 'endurance', 'stamina', 'aerobic'],
            'General Fitness': ['bodyweight', 'functional', 'compound', 'general']
        }

        exercise_types = []
        for goal in goals:
            if goal in goal_mapping:
                exercise_types.extend(goal_mapping[goal])

        return list(set(exercise_types)) if exercise_types else ['general']

    def create_weekly_schedule(self, **kwargs) -> Dict[str, Dict]:
        """Create a structured weekly schedule"""
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        schedule = {}

        # Get user's goals for custom schedule adjustments
        goals = kwargs['user_data']['fitness_goals']

        # Create schedule for each day
        for i, day in enumerate(days):
            is_rest_day = self._should_be_rest_day(day, i, goals)

            schedule[day] = {
                'type': 'Rest & Rejuvenation' if is_rest_day else self.get_day_type(i, goals),
                'schedule': self.create_day_schedule(is_rest_day=is_rest_day, **kwargs)
            }

        return schedule

    def _should_be_rest_day(self, day: str, day_index: int, goals: List[str]) -> bool:
        """Determine if a day should be a rest day based on goals"""
        if 'Muscle Gain' in goals:
            # More rest days for muscle gain
            return day in ['wednesday', 'sunday']
        elif 'Weight Loss' in goals:
            # Fewer rest days for weight loss
            return day == 'sunday'
        else:
            # Default rest schedule
            return day == 'sunday'

    def select_workout_exercises(self, exercises: List[Dict], user_data: Dict) -> List[Dict]:
        """Select exercises for a workout based on user data"""
        level = user_data['experience_level']
        goals = user_data['fitness_goals']

        # Filter exercises based on the day's focus
        day_focus = self.get_day_focus(datetime.now().strftime('%A').lower(), goals)
        relevant_exercises = [
            ex for ex in exercises
            if any(tag in ex['tags'] for tag in self.map_goals_to_types([day_focus]))
        ]

        if not relevant_exercises:
            relevant_exercises = exercises

        # Select a balanced workout
        selected = []
        exercise_types = set()

        for ex in sorted(relevant_exercises, key=lambda x: random.random()):
            ex_type = next((tag for tag in ex['tags'] if tag in ['push', 'pull', 'legs', 'core']), None)
            if len(selected) < 5 and (not ex_type or ex_type not in exercise_types):
                selected.append(ex)
                if ex_type:
                    exercise_types.add(ex_type)

        return [{
            'name': ex['name'],
            'sets': ex['difficulty_levels'][level]['sets'],
            'reps': ex['difficulty_levels'][level]['reps'],
            'form_cues': ex['form_cues'],
            'alternatives': ex.get('alternatives', [])
        } for ex in selected[:5]]

    def get_day_focus(self, day: str, goals: List[str]) -> str:
        """Get the focus for a specific day based on goals"""
        if 'Muscle Gain' in goals:
            focus_map = {
                'monday': 'Push',
                'tuesday': 'Pull',
                'thursday': 'Legs',
                'friday': 'Upper Body',
                'saturday': 'Lower Body'
            }
        else:
            focus_map = {
                'monday': 'Full Body',
                'tuesday': 'Cardio',
                'thursday': 'Strength',
                'friday': 'HIIT',
                'saturday': 'Endurance'
            }

        return focus_map.get(day, 'General Training')
