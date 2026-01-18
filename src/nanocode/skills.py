"""Skills management for nanocode."""

import os
import re
from pathlib import Path
from typing import Optional


class Skill:
    """Represents a skill loaded from a .md file."""
    
    def __init__(self, name: str, description: str, content: str, license: Optional[str] = None):
        self.name = name
        self.description = description
        self.content = content
        self.license = license
    
    def __repr__(self):
        return f"Skill(name={self.name!r}, description={self.description!r})"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    if not match:
        return {}, text
    
    frontmatter = match.group(1)
    content = match.group(2).strip()
    
    result = {}
    for line in frontmatter.strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    
    return result, content


def load_skill(filepath: str) -> Optional[Skill]:
    """Load a skill from a markdown file."""
    try:
        text = open(filepath).read()
        frontmatter, content = parse_frontmatter(text)
        
        if not frontmatter.get("name"):
            return None
        
        return Skill(
            name=frontmatter["name"],
            description=frontmatter.get("description", ""),
            content=content,
            license=frontmatter.get("license"),
        )
    except Exception:
        return None


def load_skills(skills_dir: str = "skills") -> dict[str, Skill]:
    """Load all skills from the skills directory."""
    skills = {}
    skills_path = Path(skills_dir)
    
    if not skills_path.exists():
        return skills
    
    for filepath in skills_path.glob("*.md"):
        skill = load_skill(str(filepath))
        if skill:
            skills[skill.name] = skill
    
    return skills


def format_skills_list(skills: dict[str, Skill]) -> str:
    """Format skills for display."""
    if not skills:
        return "No skills available"
    
    lines = []
    for name, skill in sorted(skills.items()):
        lines.append(f"• {name}: {skill.description}")
        if skill.license:
            lines.append(f"    License: {skill.license}")
    
    return "\n".join(lines)


def skill_context_block(skill: Skill) -> str:
    """Format skill content for inclusion in system prompt."""
    return f"""
<skill name="{skill.name}">
{skill.content}
</skill>
"""
