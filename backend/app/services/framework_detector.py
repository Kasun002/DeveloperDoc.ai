"""
Framework detection service.

This module provides utilities to automatically detect frameworks and programming
languages from user prompts using keyword matching and pattern recognition.
"""

import re
from typing import Dict, List, Optional, Tuple

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class FrameworkDetector:
    """
    Detects frameworks and programming languages from user prompts.
    
    Uses keyword matching and pattern recognition to identify which framework
    and language the user is asking about.
    """
    
    # Framework keywords and their associated languages
    FRAMEWORK_PATTERNS = {
        "nestjs": {
            "keywords": ["nestjs", "nest.js", "nest js", "@nestjs", "@controller", "@injectable", "@module"],
            "language": "TypeScript",
            "framework": "NestJS"
        },
        "react": {
            "keywords": ["react", "reactjs", "react.js", "jsx", "tsx", "usestate", "useeffect", "react component"],
            "language": "TypeScript",
            "framework": "React"
        },
        "fastapi": {
            "keywords": ["fastapi", "fast api", "@app.get", "@app.post", "pydantic", "uvicorn"],
            "language": "Python",
            "framework": "FastAPI"
        },
        "django": {
            "keywords": ["django", "django rest", "drf", "django.db", "models.model", "django views"],
            "language": "Python",
            "framework": "Django"
        },
        "express": {
            "keywords": ["express", "expressjs", "express.js", "app.get", "app.post", "express router"],
            "language": "JavaScript",
            "framework": "Express"
        },
        "vue": {
            "keywords": ["vue", "vuejs", "vue.js", "vue component", "v-model", "v-if", "v-for"],
            "language": "JavaScript",
            "framework": "Vue"
        },
        "angular": {
            "keywords": ["angular", "@angular", "@component", "@injectable", "ngmodule", "angular component"],
            "language": "TypeScript",
            "framework": "Angular"
        },
        "spring": {
            "keywords": ["spring boot", "spring", "@restcontroller", "@service", "@autowired", "springboot"],
            "language": "Java",
            "framework": "Spring Boot"
        },
        "dotnet": {
            "keywords": [".net", "dotnet", "asp.net", "c#", "csharp", "[apicontroller]", "[httpget]"],
            "language": "C#",
            "framework": ".NET Core"
        },
        "nextjs": {
            "keywords": ["next.js", "nextjs", "next js", "getserversideprops", "getstaticprops"],
            "language": "TypeScript",
            "framework": "Next.js"
        },
        "flask": {
            "keywords": ["flask", "@app.route", "flask.request", "flask app"],
            "language": "Python",
            "framework": "Flask"
        }
    }
    
    # Language-specific keywords (fallback if no framework detected)
    LANGUAGE_PATTERNS = {
        "typescript": ["typescript", "ts", "interface", "type", "enum"],
        "javascript": ["javascript", "js", "const", "let", "var", "function"],
        "python": ["python", "def", "class", "import", "from"],
        "java": ["java", "public class", "private", "protected"],
        "csharp": ["c#", "csharp", "namespace", "using system"],
        "go": ["golang", "go", "func", "package"],
        "rust": ["rust", "fn", "impl", "trait"]
    }
    
    def detect_framework(self, prompt: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect framework and language from a prompt.
        
        Args:
            prompt: User prompt text
            
        Returns:
            Tuple of (framework, language) or (None, None) if not detected
            
        Example:
            >>> detector = FrameworkDetector()
            >>> framework, language = detector.detect_framework("Create a NestJS controller")
            >>> print(framework, language)
            NestJS TypeScript
        """
        prompt_lower = prompt.lower()
        
        # Check for framework patterns
        best_match = None
        max_matches = 0
        
        for framework_key, config in self.FRAMEWORK_PATTERNS.items():
            matches = sum(1 for keyword in config["keywords"] if keyword.lower() in prompt_lower)
            
            if matches > max_matches:
                max_matches = matches
                best_match = config
        
        if best_match and max_matches > 0:
            framework = best_match["framework"]
            language = best_match["language"]
            
            logger.info(
                "framework_detected",
                framework=framework,
                language=language,
                matches=max_matches,
                prompt_preview=prompt[:100]
            )
            
            return framework, language
        
        # Fallback: try to detect language only
        for lang_key, keywords in self.LANGUAGE_PATTERNS.items():
            if any(keyword in prompt_lower for keyword in keywords):
                language = lang_key.title()
                logger.info(
                    "language_detected",
                    language=language,
                    prompt_preview=prompt[:100]
                )
                return None, language
        
        logger.info(
            "no_framework_detected",
            prompt_preview=prompt[:100]
        )
        
        return None, None
    
    def extract_context(self, prompt: str) -> Dict[str, str]:
        """
        Extract context information from a prompt.
        
        Detects framework, language, and other relevant context.
        
        Args:
            prompt: User prompt text
            
        Returns:
            Dictionary with context information
            
        Example:
            >>> detector = FrameworkDetector()
            >>> context = detector.extract_context("Create a NestJS REST API")
            >>> print(context)
            {'framework': 'NestJS', 'language': 'TypeScript'}
        """
        framework, language = self.detect_framework(prompt)
        
        context = {}
        
        if framework:
            context["framework"] = framework
        
        if language:
            context["language"] = language
        
        # Detect additional context clues
        prompt_lower = prompt.lower()
        
        # Detect component types
        if any(word in prompt_lower for word in ["controller", "api", "endpoint", "route"]):
            context["component_type"] = "controller"
        elif any(word in prompt_lower for word in ["service", "business logic", "logic"]):
            context["component_type"] = "service"
        elif any(word in prompt_lower for word in ["component", "ui", "interface", "view"]):
            context["component_type"] = "component"
        elif any(word in prompt_lower for word in ["model", "entity", "schema"]):
            context["component_type"] = "model"
        
        # Detect authentication/authorization context
        if any(word in prompt_lower for word in ["auth", "login", "register", "jwt", "token"]):
            context["feature"] = "authentication"
        elif any(word in prompt_lower for word in ["crud", "create", "read", "update", "delete"]):
            context["feature"] = "crud"
        
        return context


# Global framework detector instance
framework_detector = FrameworkDetector()


def detect_framework_from_prompt(prompt: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Convenience function to detect framework from prompt.
    
    Args:
        prompt: User prompt text
        
    Returns:
        Tuple of (framework, language)
    """
    return framework_detector.detect_framework(prompt)


def extract_context_from_prompt(prompt: str) -> Dict[str, str]:
    """
    Convenience function to extract context from prompt.
    
    Args:
        prompt: User prompt text
        
    Returns:
        Dictionary with context information
    """
    return framework_detector.extract_context(prompt)
