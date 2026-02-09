"""
Code Generation Agent for framework-aware code generation.

This module implements the Code Generation Agent that generates syntactically
correct, framework-compliant code using LLM with optional documentation context.
"""

import logging
from typing import List, Optional

from openai import AsyncOpenAI
import openai

from app.core.config import settings
from app.schemas.agent import CodeGenerationResult, DocumentationResult
from app.utils.retry import llm_api_retry

logger = logging.getLogger(__name__)


class CodeGenAgent:
    """
    Agent for generating framework-aware, syntactically correct code.
    
    This agent generates code using LLM with system prompts optimized for
    framework-specific generation. It incorporates documentation context from
    the Documentation Search Agent and validates syntax before returning results.
    
    Attributes:
        client: AsyncOpenAI client for LLM API calls
        model: LLM model name (default: gpt-4)
        max_retries: Maximum number of syntax validation retries
    """
    
    def __init__(
        self,
        client: Optional[AsyncOpenAI] = None,
        model: str = "gpt-4",
        max_retries: int = 2
    ):
        """
        Initialize the Code Generation Agent.
        
        Args:
            client: AsyncOpenAI client instance (creates new if None)
            model: LLM model name (default: gpt-4)
            max_retries: Maximum syntax validation retries (default: 2)
        """
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = model
        self.max_retries = max_retries
    
    async def generate_code(
        self,
        prompt: str,
        documentation_context: Optional[List[DocumentationResult]] = None,
        framework: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> CodeGenerationResult:
        """
        Generate syntactically correct, framework-compliant code.
        
        Uses LLM with framework-specific system prompts and incorporates
        documentation context as examples and best practices. Validates
        syntax and retries on errors.
        
        Args:
            prompt: User's code generation request
            documentation_context: Optional documentation results for context
            framework: Target framework (e.g., "NestJS", "React", "FastAPI")
            trace_id: Unique identifier for request tracing
            
        Returns:
            CodeGenerationResult: Generated code with validation status
            
        Raises:
            ValueError: If prompt is empty
            ConnectionError: If LLM API call fails after retries
            
        Example:
            >>> agent = CodeGenAgent()
            >>> result = await agent.generate_code(
            ...     "Create a NestJS controller for user authentication",
            ...     framework="NestJS"
            ... )
            >>> print(result.code)
            >>> print(result.syntax_valid)
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        logger.info(
            "Code generation started",
            extra={
                "trace_id": trace_id,
                "framework": framework,
                "has_documentation_context": documentation_context is not None,
                "context_count": len(documentation_context) if documentation_context else 0
            }
        )
        
        # Build system prompt based on framework
        system_prompt = self._build_system_prompt(framework, documentation_context)
        
        # Build user prompt with documentation context
        user_prompt = self._build_user_prompt(prompt, documentation_context)
        
        # Detect language from framework or prompt
        language = self._detect_language(framework, prompt)
        
        # Track tokens used
        total_tokens = 0
        
        # Attempt code generation with retries for syntax errors
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(
                    f"Code generation attempt {attempt + 1}/{self.max_retries + 1}",
                    extra={
                        "trace_id": trace_id,
                        "attempt": attempt + 1,
                        "framework": framework
                    }
                )
                
                # Call LLM API with retry logic
                @llm_api_retry
                async def _call_llm():
                    return await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.2,  # Lower temperature for more deterministic code
                        max_tokens=2000
                    )
                
                response = await _call_llm()
                
                generated_code = response.choices[0].message.content.strip()
                tokens_used = response.usage.total_tokens
                total_tokens += tokens_used
                
                logger.info(
                    "LLM response received",
                    extra={
                        "trace_id": trace_id,
                        "tokens_used": tokens_used,
                        "code_length": len(generated_code)
                    }
                )
                
                # Extract code from markdown code blocks if present
                generated_code = self._extract_code_from_markdown(generated_code)
                
                # Validate syntax
                from app.agents.syntax_validator import SyntaxValidator
                validator = SyntaxValidator()
                validation_result = validator.validate_syntax(generated_code, language)
                
                if validation_result["valid"]:
                    logger.info(
                        "Code generation successful",
                        extra={
                            "trace_id": trace_id,
                            "language": language,
                            "framework": framework,
                            "total_tokens": total_tokens,
                            "attempts": attempt + 1
                        }
                    )
                    
                    # Extract documentation sources
                    doc_sources = []
                    if documentation_context:
                        doc_sources = [doc.source for doc in documentation_context]
                    
                    return CodeGenerationResult(
                        code=generated_code,
                        language=language,
                        framework=framework,
                        syntax_valid=True,
                        validation_errors=[],
                        tokens_used=total_tokens,
                        documentation_sources=doc_sources
                    )
                else:
                    # Syntax validation failed
                    errors = validation_result.get("errors", [])
                    logger.warning(
                        f"Syntax validation failed on attempt {attempt + 1}",
                        extra={
                            "trace_id": trace_id,
                            "errors": errors,
                            "attempt": attempt + 1
                        }
                    )
                    
                    if attempt < self.max_retries:
                        # Retry with error feedback
                        error_feedback = "\n".join(errors)
                        user_prompt = f"{user_prompt}\n\nPrevious attempt had syntax errors:\n{error_feedback}\n\nPlease fix these errors and generate valid {language} code."
                    else:
                        # Max retries reached, return with errors
                        logger.error(
                            "Max retries reached, returning code with syntax errors",
                            extra={
                                "trace_id": trace_id,
                                "errors": errors,
                                "attempts": attempt + 1
                            }
                        )
                        
                        doc_sources = []
                        if documentation_context:
                            doc_sources = [doc.source for doc in documentation_context]
                        
                        return CodeGenerationResult(
                            code=generated_code,
                            language=language,
                            framework=framework,
                            syntax_valid=False,
                            validation_errors=errors,
                            tokens_used=total_tokens,
                            documentation_sources=doc_sources
                        )
                        
            except (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError) as e:
                # LLM API specific errors - log with trace_id
                logger.error(
                    f"LLM API error on attempt {attempt + 1}",
                    extra={
                        "trace_id": trace_id,
                        "error_type": type(e).__name__,
                        "error": str(e),
                        "attempt": attempt + 1
                    },
                    exc_info=True
                )
                
                if attempt >= self.max_retries:
                    # Return error result with descriptive message
                    return CodeGenerationResult(
                        code="",
                        language=language,
                        framework=framework,
                        syntax_valid=False,
                        validation_errors=[
                            f"LLM API failed after {self.max_retries + 1} attempts: {type(e).__name__} - {str(e)}",
                            f"trace_id: {trace_id}"
                        ],
                        tokens_used=total_tokens,
                        documentation_sources=[]
                    )
            except Exception as e:
                logger.error(
                    f"Code generation error on attempt {attempt + 1}",
                    extra={
                        "trace_id": trace_id,
                        "error_type": type(e).__name__,
                        "error": str(e),
                        "attempt": attempt + 1
                    },
                    exc_info=True
                )
                
                if attempt >= self.max_retries:
                    raise ConnectionError(
                        f"Code generation failed after {self.max_retries + 1} attempts (trace_id: {trace_id}): {str(e)}"
                    )
        
        # Should not reach here, but return error result as fallback
        return CodeGenerationResult(
            code="",
            language=language,
            framework=framework,
            syntax_valid=False,
            validation_errors=["Code generation failed after maximum retries"],
            tokens_used=total_tokens,
            documentation_sources=[]
        )
    
    def _build_system_prompt(
        self,
        framework: Optional[str],
        documentation_context: Optional[List[DocumentationResult]]
    ) -> str:
        """
        Build framework-specific system prompt for code generation.
        
        Args:
            framework: Target framework name
            documentation_context: Optional documentation for context
            
        Returns:
            str: System prompt optimized for the framework
        """
        base_prompt = """You are an expert software engineer specializing in generating high-quality, production-ready code.

Your responsibilities:
1. Generate syntactically correct code that follows language best practices
2. Follow framework-specific conventions and patterns
3. Write clean, readable, and maintainable code
4. Include appropriate comments for complex logic
5. Use proper error handling and validation
6. Follow the framework's recommended project structure

Important guidelines:
- Generate ONLY the code requested, no explanations unless asked
- Ensure all imports and dependencies are included
- Use proper typing/type hints where applicable
- Follow the framework's naming conventions
- Include necessary decorators, annotations, or attributes"""
        
        if framework:
            framework_specific = self._get_framework_specific_guidance(framework)
            base_prompt += f"\n\n{framework_specific}"
        
        if documentation_context:
            base_prompt += "\n\nYou have access to relevant framework documentation excerpts. Use these as reference for best practices and patterns."
        
        return base_prompt
    
    def _get_framework_specific_guidance(self, framework: str) -> str:
        """
        Get framework-specific guidance for code generation.
        
        Args:
            framework: Framework name
            
        Returns:
            str: Framework-specific guidance
        """
        guidance_map = {
            "NestJS": """Framework: NestJS (TypeScript)
- Use decorators: @Controller(), @Get(), @Post(), @Injectable(), etc.
- Follow dependency injection patterns
- Use proper module structure with @Module()
- Implement DTOs with class-validator decorators
- Use async/await for asynchronous operations
- Follow NestJS naming conventions (e.g., *.controller.ts, *.service.ts)""",
            
            "React": """Framework: React (JavaScript/TypeScript)
- Use functional components with hooks
- Follow React hooks rules (useState, useEffect, useCallback, useMemo)
- Use proper prop types or TypeScript interfaces
- Implement proper component composition
- Follow React naming conventions (PascalCase for components)
- Use modern ES6+ syntax""",
            
            "FastAPI": """Framework: FastAPI (Python)
- Use type hints for all function parameters and returns
- Use Pydantic models for request/response validation
- Implement proper dependency injection with Depends()
- Use async def for asynchronous endpoints
- Follow Python naming conventions (snake_case)
- Include proper HTTP status codes and response models""",
            
            "Spring Boot": """Framework: Spring Boot (Java)
- Use annotations: @RestController, @Service, @Repository, @Autowired
- Follow dependency injection with constructor injection
- Use proper exception handling with @ExceptionHandler
- Implement DTOs and entities separately
- Follow Java naming conventions (camelCase for methods, PascalCase for classes)
- Use Optional for nullable values""",
            
            ".NET Core": """Framework: .NET Core (C#)
- Use attributes: [ApiController], [HttpGet], [HttpPost], etc.
- Follow dependency injection patterns with IServiceCollection
- Use async/await for asynchronous operations
- Implement proper model validation with data annotations
- Follow C# naming conventions (PascalCase for public members)
- Use nullable reference types where appropriate""",
            
            "Vue.js": """Framework: Vue.js (JavaScript/TypeScript)
- Use Composition API with setup() or <script setup>
- Follow Vue 3 patterns with ref, reactive, computed
- Use proper component props and emits
- Implement proper lifecycle hooks
- Follow Vue naming conventions (kebab-case for components in templates)
- Use modern ES6+ syntax""",
            
            "Angular": """Framework: Angular (TypeScript)
- Use decorators: @Component, @Injectable, @Input, @Output
- Follow dependency injection patterns
- Use RxJS observables for async operations
- Implement proper component lifecycle hooks
- Follow Angular naming conventions (*.component.ts, *.service.ts)
- Use TypeScript strict mode""",
            
            "Django": """Framework: Django (Python)
- Use class-based views or function-based views appropriately
- Follow Django ORM patterns for models
- Implement proper URL routing
- Use Django forms or serializers (DRF)
- Follow Python naming conventions (snake_case)
- Include proper middleware and authentication""",
            
            "Express.js": """Framework: Express.js (JavaScript/TypeScript)
- Use middleware patterns properly
- Implement proper route handlers
- Use async/await for asynchronous operations
- Follow RESTful API conventions
- Include proper error handling middleware
- Use modern ES6+ syntax"""
        }
        
        return guidance_map.get(framework, f"Framework: {framework}\n- Follow {framework} best practices and conventions")
    
    def _build_user_prompt(
        self,
        prompt: str,
        documentation_context: Optional[List[DocumentationResult]]
    ) -> str:
        """
        Build user prompt with documentation context.
        
        Args:
            prompt: Original user prompt
            documentation_context: Optional documentation results
            
        Returns:
            str: Enhanced user prompt with context
        """
        if not documentation_context:
            return prompt
        
        # Add documentation context as examples
        context_text = "\n\n=== Relevant Documentation ===\n"
        for i, doc in enumerate(documentation_context[:3], 1):  # Use top 3 results
            context_text += f"\n[Example {i} from {doc.framework} - {doc.source}]\n"
            context_text += f"{doc.content[:500]}...\n"  # Limit context length
        
        context_text += "\n=== End Documentation ===\n\n"
        context_text += "Based on the documentation above, please generate the requested code:\n\n"
        
        return context_text + prompt
    
    def _detect_language(self, framework: Optional[str], prompt: str) -> str:
        """
        Detect programming language from framework or prompt.
        
        Args:
            framework: Framework name
            prompt: User prompt
            
        Returns:
            str: Detected language
        """
        # Framework to language mapping
        framework_language_map = {
            "NestJS": "TypeScript",
            "React": "JavaScript",
            "FastAPI": "Python",
            "Spring Boot": "Java",
            ".NET Core": "C#",
            "Vue.js": "JavaScript",
            "Angular": "TypeScript",
            "Django": "Python",
            "Express.js": "JavaScript"
        }
        
        if framework and framework in framework_language_map:
            return framework_language_map[framework]
        
        # Try to detect from prompt
        prompt_lower = prompt.lower()
        if any(word in prompt_lower for word in ["python", "fastapi", "django", "flask"]):
            return "Python"
        elif any(word in prompt_lower for word in ["typescript", "nestjs", "angular"]):
            return "TypeScript"
        elif any(word in prompt_lower for word in ["javascript", "react", "vue", "express", "node"]):
            return "JavaScript"
        elif any(word in prompt_lower for word in ["java", "spring"]):
            return "Java"
        elif any(word in prompt_lower for word in ["c#", "csharp", ".net", "dotnet"]):
            return "C#"
        
        # Default to Python
        return "Python"
    
    def _extract_code_from_markdown(self, text: str) -> str:
        """
        Extract code from markdown code blocks.
        
        Args:
            text: Text potentially containing markdown code blocks
            
        Returns:
            str: Extracted code or original text
        """
        # Check if text contains markdown code blocks
        if "```" in text:
            # Extract code between ``` markers
            parts = text.split("```")
            if len(parts) >= 3:
                # Get the code block (skip language identifier if present)
                code_block = parts[1]
                # Remove language identifier from first line if present
                lines = code_block.split("\n")
                if lines and lines[0].strip() and not any(c in lines[0] for c in ["{", "}", "(", ")", ";"]):
                    # First line is likely language identifier
                    code_block = "\n".join(lines[1:])
                return code_block.strip()
        
        return text.strip()
    
    def get_agent_info(self) -> dict:
        """
        Get information about the agent configuration.
        
        Returns:
            dict: Agent configuration including model and retry settings
        """
        return {
            "agent_type": "code_generation",
            "model": self.model,
            "max_retries": self.max_retries,
            "supported_frameworks": [
                "NestJS", "React", "FastAPI", "Spring Boot", ".NET Core",
                "Vue.js", "Angular", "Django", "Express.js"
            ]
        }


# Global code generation agent instance
code_gen_agent = CodeGenAgent()


async def get_code_gen_agent() -> CodeGenAgent:
    """
    Dependency injection function for FastAPI endpoints.
    
    Returns:
        CodeGenAgent: Global code generation agent instance
    """
    return code_gen_agent
