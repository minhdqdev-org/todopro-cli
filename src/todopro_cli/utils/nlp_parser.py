"""Local natural language parsing for tasks.

Provides date parsing, priority extraction, project/label detection
without requiring backend API.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

try:
    import dateparser
    HAS_DATEPARSER = True
except ImportError:
    HAS_DATEPARSER = False


class LocalNLPParser:
    """Parse natural language task descriptions locally."""
    
    def __init__(self):
        """Initialize the parser."""
        self.priority_patterns = {
            r'\bp1\b|!!1|!!!|urgent': 4,
            r'\bp2\b|!!2|high': 3,
            r'\bp3\b|!!3|medium': 2,
            r'\bp4\b|!!4|low': 1,
        }
    
    def parse(self, text: str) -> dict[str, Any]:
        """Parse task text for metadata.
        
        Args:
            text: Natural language task description
            
        Returns:
            dict with parsed metadata:
                - content: Cleaned task content
                - due_date: Parsed datetime or None
                - priority: 1-4 or None
                - project_name: Extracted project or None
                - labels: List of extracted labels
        """
        result = {
            'content': text,
            'due_date': None,
            'priority': None,
            'project_name': None,
            'labels': [],
        }
        
        # Extract priority
        for pattern, priority in self.priority_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                result['priority'] = priority
                # Remove priority marker from text
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
                break
        
        # Extract project (#ProjectName)
        project_match = re.search(r'#(\w+)', text)
        if project_match:
            result['project_name'] = project_match.group(1)
            text = text.replace(project_match.group(0), '')
        
        # Extract labels (@label)
        label_matches = re.findall(r'@(\w+)', text)
        if label_matches:
            result['labels'] = label_matches
            # Remove labels from text
            text = re.sub(r'@\w+', '', text)
        
        # Parse date
        result['due_date'] = self._parse_date(text)
        if result['due_date']:
            # Remove parsed date phrases from text
            text = self._remove_date_phrases(text)
        
        # Clean up the content
        result['content'] = ' '.join(text.split()).strip()
        
        return result
    
    def _parse_date(self, text: str) -> datetime | None:
        """Parse date from text.
        
        Args:
            text: Text potentially containing date phrase
            
        Returns:
            Parsed datetime or None
        """
        if HAS_DATEPARSER:
            # Use dateparser for robust parsing
            parsed = dateparser.parse(
                text,
                settings={
                    'PREFER_DATES_FROM': 'future',
                    'RELATIVE_BASE': datetime.now(),
                }
            )
            return parsed
        else:
            # Fallback to simple patterns
            return self._simple_date_parse(text)
    
    def _simple_date_parse(self, text: str) -> datetime | None:
        """Simple date parsing fallback without dateparser.
        
        Args:
            text: Text to parse
            
        Returns:
            Parsed datetime or None
        """
        now = datetime.now()
        text_lower = text.lower()
        
        # Today
        if 'today' in text_lower:
            return now.replace(hour=23, minute=59, second=59)
        
        # Tomorrow
        if 'tomorrow' in text_lower:
            return (now + timedelta(days=1)).replace(hour=23, minute=59, second=59)
        
        # Next week
        if 'next week' in text_lower:
            return (now + timedelta(days=7)).replace(hour=23, minute=59, second=59)
        
        # In N days
        match = re.search(r'in (\d+) days?', text_lower)
        if match:
            days = int(match.group(1))
            return (now + timedelta(days=days)).replace(hour=23, minute=59, second=59)
        
        # Weekdays
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        for day_name, day_num in weekdays.items():
            if day_name in text_lower:
                # Find next occurrence of this weekday
                current_weekday = now.weekday()
                days_ahead = (day_num - current_weekday) % 7
                if days_ahead == 0:
                    days_ahead = 7  # Next week if today
                target = now + timedelta(days=days_ahead)
                return target.replace(hour=23, minute=59, second=59)
        
        return None
    
    def _remove_date_phrases(self, text: str) -> str:
        """Remove common date phrases from text.
        
        Args:
            text: Text with date phrases
            
        Returns:
            Text with date phrases removed
        """
        date_phrases = [
            r'\btoday\b',
            r'\btomorrow\b',
            r'\bnext week\b',
            r'\bin \d+ days?\b',
            r'\bmonday\b', r'\btuesday\b', r'\bwednesday\b', r'\bthursday\b',
            r'\bfriday\b', r'\bsaturday\b', r'\bsunday\b',
            r'\bat \d+:\d+\s*[ap]m\b',
            r'\bat \d+[ap]m\b',
        ]
        
        for pattern in date_phrases:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text


def parse_natural_language(text: str) -> dict[str, Any]:
    """Convenience function to parse natural language task description.
    
    Args:
        text: Natural language task description
        
    Returns:
        Parsed metadata dict
        
    Example:
        >>> parse_natural_language("Review PR tomorrow #Work p1 @urgent")
        {
            'content': 'Review PR',
            'due_date': datetime(...),
            'priority': 4,
            'project_name': 'Work',
            'labels': ['urgent']
        }
    """
    parser = LocalNLPParser()
    return parser.parse(text)
