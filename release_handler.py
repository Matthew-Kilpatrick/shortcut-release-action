#!/usr/bin/env python3

import os
import re
import requests
import subprocess
import json
import sys
import logging
import argparse
from typing import List, Dict, Tuple
from semantic_version import Version
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ReleaseHandler:
    def __init__(self):
        self.shortcut_token = os.getenv('SHORTCUT_API_TOKEN')
        if not self.shortcut_token:
            logger.error("SHORTCUT_API_TOKEN environment variable is not set")
            sys.exit(1)
            
        self.shortcut_headers = {
            'Content-Type': 'application/json',
            'Shortcut-Token': self.shortcut_token
        }
        self.shortcut_api_url = 'https://api.app.shortcut.com/api/v3'

    def get_commits_between_releases(self, base: str, head: str, repo_path: str = None) -> List[str]:
        """Get commit messages between two points using local git."""
        try:
            cmd = ['git', 'log', f'{base}..{head}', '--format=%s']
            if repo_path:
                cmd = ['git', '-C', repo_path, 'log', f'{base}..{head}', '--format=%s']
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            commits = result.stdout.strip().split('\n')
            logger.info(f"Found {len(commits)} commits between {base} and {head}")
            return commits
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting commits: {e}")
            return []

    def extract_story_ids(self, commit_messages: List[str]) -> List[str]:
        """Extract Shortcut story IDs from commit messages."""
        story_pattern = r'sc-(\d+)'
        story_ids = []
        for message in commit_messages:
            matches = re.finditer(story_pattern, message.lower())
            story_ids.extend([f"SC-{match.group(1)}" for match in matches])
        return list(set(story_ids))

    def get_story_details(self, story_id: str) -> Dict:
        """Get story details from Shortcut API."""
        try:
            numeric_id = story_id.lower().replace('sc-', '')
            logger.info(f"Fetching story details for {story_id}")
            response = requests.get(
                f"{self.shortcut_api_url}/stories/{numeric_id}",
                headers=self.shortcut_headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching story {story_id}: {e}")
            return {}

    def categorize_stories(self, story_ids: List[str]) -> Dict[str, List[Dict]]:
        """Categorize stories by type."""
        categories = {
            'feature': [],
            'bug': [],
            'chore': []
        }
        
        for story_id in story_ids:
            story = self.get_story_details(story_id)
            story_type = story.get('story_type', '').lower()
            if story_type in categories:
                categories[story_type].append({
                    'id': story_id,
                    'name': story.get('name', ''),
                    'description': story.get('description', '')
                })
        
        return categories

    def determine_version_bump(self, categories: Dict[str, List[Dict]]) -> str:
        """Determine version bump based on story types."""
        if categories['feature']:
            return 'minor'
        elif categories['bug']:
            return 'patch'
        return 'patch'

    def generate_release_notes(self, categories: Dict[str, List[Dict]], include_story_links: bool = False) -> str:
        """Generate release notes from categorized stories.
        
        Args:
            categories: Dictionary of categorized stories
            include_story_links: If True, will include markdown links to the stories. Defaults to False.
        """
        notes = []
        
        if categories['feature']:
            notes.append("## 🚀 Features")
            for story in categories['feature']:
                if include_story_links:
                    notes.append(f"- [{story['name']}](https://app.shortcut.com/story/{story['id'].lower()})")
                else:
                    notes.append(f"- {story['name']}")
        
        if categories['bug']:
            notes.append("\n## 🐛 Bug Fixes")
            for story in categories['bug']:
                if include_story_links:
                    notes.append(f"- [{story['name']}](https://app.shortcut.com/story/{story['id'].lower()})")
                else:
                    notes.append(f"- {story['name']}")
        
        if categories['chore']:
            notes.append("\n## 🔧 Chores")
            for story in categories['chore']:
                if include_story_links:
                    notes.append(f"- [{story['name']}](https://app.shortcut.com/story/{story['id'].lower()})")
                else:
                    notes.append(f"- {story['name']}")
        
        return "\n".join(notes)

    def get_current_tag(self, repo_path: str = None) -> str:
        """Get the tag at the current commit if it exists."""
        try:
            cmd = ['git', 'tag', '--points-at', 'HEAD']
            if repo_path:
                cmd = ['git', '-C', repo_path, 'tag', '--points-at', 'HEAD']
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            tags = result.stdout.strip().split('\n')
            # Filter for version tags
            version_tags = [tag for tag in tags if re.match(r'^v[0-9]+\.[0-9]+\.[0-9]+$', tag)]
            if version_tags:
                logger.info(f"Found existing version tag at current commit: {version_tags[0]}")
                return version_tags[0]
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"Error checking current tags: {e}")
            return None

def main():
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Generate release information')
        parser.add_argument('--prev-version', required=True, help='Previous version tag (e.g., v1.2.3)')
        parser.add_argument('--repo-path', help='Optional repository path')
        parser.add_argument('--include-story-links', action='store_true', help='Include Shortcut story links in release notes')
        args = parser.parse_args()

        handler = ReleaseHandler()
        
        # Parse previous version
        try:
            prev_version = Version(args.prev_version.lstrip('v'))
            logger.info(f"Using previous version: {args.prev_version}")
        except ValueError as e:
            logger.error(f"Invalid version format: {args.prev_version}")
            sys.exit(1)
        
        # Get commits between releases and process story IDs
        commit_messages = handler.get_commits_between_releases(args.prev_version, 'HEAD', args.repo_path)
        logger.info(f"Commit messages: {commit_messages}")
        
        story_ids = handler.extract_story_ids(commit_messages)
        logger.info(f"Found story IDs: {story_ids}")
        
        if not story_ids:
            logger.warning("No story IDs found in commit messages")
        
        categories = handler.categorize_stories(story_ids)
        logger.info(f"Categorized stories: {json.dumps(categories, indent=2)}")
        
        # Check if current commit already has a version tag
        current_tag = handler.get_current_tag(args.repo_path)
        if current_tag:
            logger.info(f"Reusing existing tag: {current_tag}")
            new_version = Version(current_tag.lstrip('v'))
        else:
            # Determine new version
            bump_type = handler.determine_version_bump(categories)
            new_version = getattr(prev_version, f"next_{bump_type}")()
            logger.info(f"New version: v{new_version} (bump type: {bump_type})")
        
        # Generate release notes
        release_notes = handler.generate_release_notes(categories, include_story_links=args.include_story_links)
        logger.info(f"Generated release notes: {release_notes}")
        
        # Output tag and release notes in a format that can be used by GitHub Actions
        output = {
            "tag": f"v{new_version}",
            "release_notes": release_notes
        }
        json_output = json.dumps(output)
        print(json_output)
        
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
