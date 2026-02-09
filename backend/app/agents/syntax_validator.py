"""
Syntax Validator for multi-language code validation.

This module implements syntax validation for multiple programming languages
including Python, JavaScript, TypeScript, Java, and C#. It uses language-specific
parsers to validate code syntax before returning generated code to users.
"""

import ast
import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)


class SyntaxValidator:
    """
    Multi-language syntax validator.
    
    Validates code syntax for various programming languages using appropriate
    parsers. Supports Python (ast), JavaScript (basic validation), TypeScript
    (basic validation), Java (basic validation), and C# (basic validation).
    
    For languages without native Python parsers, performs basic structural
    validation to catch common syntax errors.
    """
    
    def __init__(self):
        """Initialize the syntax validator."""
        self.supported_languages = [
            "Python",
            "JavaScript",
            "TypeScript",
            "Java",
            "C#"
        ]
    
    def validate_syntax(self, code: str, language: str) -> Dict[str, any]:
        """
        Validate code syntax for the specified language.
        
        Args:
            code: Code string to validate
            language: Programming language (Python, JavaScript, TypeScript, Java, C#)
            
        Returns:
            Dict with keys:
                - valid (bool): Whether code is syntactically valid
                - errors (List[str]): List of error messages if invalid
                - language (str): Language that was validated
                
        Example:
            >>> validator = SyntaxValidator()
            >>> result = validator.validate_syntax("print('hello')", "Python")
            >>> result["valid"]
            True
            >>> result = validator.validate_syntax("print('hello'", "Python")
            >>> result["valid"]
            False
            >>> result["errors"]
            ["SyntaxError: unexpected EOF while parsing"]
        """
        if not code or not code.strip():
            return {
                "valid": False,
                "errors": ["Code is empty"],
                "language": language
            }
        
        logger.info(
            f"Validating {language} code",
            extra={
                "language": language,
                "code_length": len(code)
            }
        )
        
        # Route to appropriate validator
        if language == "Python":
            return self._validate_python(code)
        elif language == "JavaScript":
            return self._validate_javascript(code)
        elif language == "TypeScript":
            return self._validate_typescript(code)
        elif language == "Java":
            return self._validate_java(code)
        elif language == "C#":
            return self._validate_csharp(code)
        else:
            # Unknown language, perform basic validation
            logger.warning(
                f"Unknown language {language}, performing basic validation",
                extra={"language": language}
            )
            return self._validate_basic(code, language)
    
    def _validate_python(self, code: str) -> Dict[str, any]:
        """
        Validate Python code using ast module.
        
        Args:
            code: Python code string
            
        Returns:
            Dict with validation result
        """
        try:
            ast.parse(code)
            logger.info("Python code validation successful")
            return {
                "valid": True,
                "errors": [],
                "language": "Python"
            }
        except SyntaxError as e:
            error_msg = f"SyntaxError at line {e.lineno}: {e.msg}"
            logger.warning(
                f"Python syntax validation failed",
                extra={"error": error_msg}
            )
            return {
                "valid": False,
                "errors": [error_msg],
                "language": "Python"
            }
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            logger.error(
                f"Python validation error",
                extra={"error": error_msg},
                exc_info=True
            )
            return {
                "valid": False,
                "errors": [error_msg],
                "language": "Python"
            }
    
    def _validate_javascript(self, code: str) -> Dict[str, any]:
        """
        Validate JavaScript code using basic structural checks.
        
        Note: This is a basic validator. For production use, consider
        integrating with Node.js-based parsers like esprima or acorn.
        
        Args:
            code: JavaScript code string
            
        Returns:
            Dict with validation result
        """
        errors = []
        
        # Check for balanced braces, brackets, and parentheses
        balance_errors = self._check_balanced_delimiters(code)
        if balance_errors:
            errors.extend(balance_errors)
        
        # Check for common syntax errors
        syntax_errors = self._check_javascript_syntax(code)
        if syntax_errors:
            errors.extend(syntax_errors)
        
        if errors:
            logger.warning(
                f"JavaScript syntax validation failed",
                extra={"errors": errors}
            )
            return {
                "valid": False,
                "errors": errors,
                "language": "JavaScript"
            }
        
        logger.info("JavaScript code validation successful")
        return {
            "valid": True,
            "errors": [],
            "language": "JavaScript"
        }
    
    def _validate_typescript(self, code: str) -> Dict[str, any]:
        """
        Validate TypeScript code using basic structural checks.
        
        Note: This is a basic validator. For production use, consider
        integrating with TypeScript compiler API.
        
        Args:
            code: TypeScript code string
            
        Returns:
            Dict with validation result
        """
        errors = []
        
        # Check for balanced braces, brackets, and parentheses
        balance_errors = self._check_balanced_delimiters(code)
        if balance_errors:
            errors.extend(balance_errors)
        
        # Check for common syntax errors (similar to JavaScript)
        syntax_errors = self._check_javascript_syntax(code)
        if syntax_errors:
            errors.extend(syntax_errors)
        
        # TypeScript-specific checks
        typescript_errors = self._check_typescript_syntax(code)
        if typescript_errors:
            errors.extend(typescript_errors)
        
        if errors:
            logger.warning(
                f"TypeScript syntax validation failed",
                extra={"errors": errors}
            )
            return {
                "valid": False,
                "errors": errors,
                "language": "TypeScript"
            }
        
        logger.info("TypeScript code validation successful")
        return {
            "valid": True,
            "errors": [],
            "language": "TypeScript"
        }
    
    def _validate_java(self, code: str) -> Dict[str, any]:
        """
        Validate Java code using basic structural checks.
        
        Note: This is a basic validator. For production use, consider
        integrating with Java compiler or parser libraries.
        
        Args:
            code: Java code string
            
        Returns:
            Dict with validation result
        """
        errors = []
        
        # Check for balanced braces, brackets, and parentheses
        balance_errors = self._check_balanced_delimiters(code)
        if balance_errors:
            errors.extend(balance_errors)
        
        # Java-specific checks
        java_errors = self._check_java_syntax(code)
        if java_errors:
            errors.extend(java_errors)
        
        if errors:
            logger.warning(
                f"Java syntax validation failed",
                extra={"errors": errors}
            )
            return {
                "valid": False,
                "errors": errors,
                "language": "Java"
            }
        
        logger.info("Java code validation successful")
        return {
            "valid": True,
            "errors": [],
            "language": "Java"
        }
    
    def _validate_csharp(self, code: str) -> Dict[str, any]:
        """
        Validate C# code using basic structural checks.
        
        Note: This is a basic validator. For production use, consider
        integrating with Roslyn compiler API.
        
        Args:
            code: C# code string
            
        Returns:
            Dict with validation result
        """
        errors = []
        
        # Check for balanced braces, brackets, and parentheses
        balance_errors = self._check_balanced_delimiters(code)
        if balance_errors:
            errors.extend(balance_errors)
        
        # C#-specific checks
        csharp_errors = self._check_csharp_syntax(code)
        if csharp_errors:
            errors.extend(csharp_errors)
        
        if errors:
            logger.warning(
                f"C# syntax validation failed",
                extra={"errors": errors}
            )
            return {
                "valid": False,
                "errors": errors,
                "language": "C#"
            }
        
        logger.info("C# code validation successful")
        return {
            "valid": True,
            "errors": [],
            "language": "C#"
        }
    
    def _validate_basic(self, code: str, language: str) -> Dict[str, any]:
        """
        Basic validation for unknown languages.
        
        Args:
            code: Code string
            language: Language name
            
        Returns:
            Dict with validation result
        """
        errors = []
        
        # Check for balanced braces, brackets, and parentheses
        balance_errors = self._check_balanced_delimiters(code)
        if balance_errors:
            errors.extend(balance_errors)
        
        if errors:
            return {
                "valid": False,
                "errors": errors,
                "language": language
            }
        
        return {
            "valid": True,
            "errors": [],
            "language": language
        }
    
    def _check_balanced_delimiters(self, code: str) -> List[str]:
        """
        Check if braces, brackets, and parentheses are balanced.
        
        Args:
            code: Code string
            
        Returns:
            List of error messages (empty if balanced)
        """
        errors = []
        stack = []
        pairs = {')': '(', '}': '{', ']': '['}
        line_num = 1
        
        # Remove string literals and comments to avoid false positives
        code_cleaned = self._remove_strings_and_comments(code)
        
        for char in code_cleaned:
            if char == '\n':
                line_num += 1
            elif char in '({[':
                stack.append((char, line_num))
            elif char in ')}]':
                if not stack:
                    errors.append(f"Unmatched closing '{char}' at line {line_num}")
                else:
                    opening, opening_line = stack.pop()
                    if opening != pairs[char]:
                        errors.append(
                            f"Mismatched delimiter: expected '{opening}' but found '{char}' at line {line_num}"
                        )
        
        # Check for unclosed delimiters
        for opening, line in stack:
            errors.append(f"Unclosed '{opening}' from line {line}")
        
        return errors
    
    def _remove_strings_and_comments(self, code: str) -> str:
        """
        Remove string literals and comments from code.
        
        This helps avoid false positives when checking delimiter balance.
        
        Args:
            code: Code string
            
        Returns:
            Code with strings and comments removed
        """
        # Remove single-line comments (// and #)
        code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        code = re.sub(r'#.*?$', '', code, flags=re.MULTILINE)
        
        # Remove multi-line comments (/* */ and """ """)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
        code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
        
        # Remove string literals
        code = re.sub(r'"(?:[^"\\]|\\.)*"', '', code)
        code = re.sub(r"'(?:[^'\\]|\\.)*'", '', code)
        code = re.sub(r'`(?:[^`\\]|\\.)*`', '', code)
        
        return code
    
    def _check_javascript_syntax(self, code: str) -> List[str]:
        """
        Check for common JavaScript syntax errors.
        
        Args:
            code: JavaScript code string
            
        Returns:
            List of error messages
        """
        errors = []
        
        # Check for function declarations without body
        if re.search(r'function\s+\w+\s*\([^)]*\)\s*;', code):
            errors.append("Function declaration without body")
        
        # Check for arrow functions without body or expression
        if re.search(r'=>\s*;', code):
            errors.append("Arrow function without body or expression")
        
        return errors
    
    def _check_typescript_syntax(self, code: str) -> List[str]:
        """
        Check for TypeScript-specific syntax errors.
        
        Args:
            code: TypeScript code string
            
        Returns:
            List of error messages
        """
        errors = []
        
        # Check for interface declarations without body
        if re.search(r'interface\s+\w+\s*;', code):
            errors.append("Interface declaration without body")
        
        # Check for type declarations without definition
        if re.search(r'type\s+\w+\s*;', code):
            errors.append("Type declaration without definition")
        
        return errors
    
    def _check_java_syntax(self, code: str) -> List[str]:
        """
        Check for common Java syntax errors.
        
        Args:
            code: Java code string
            
        Returns:
            List of error messages
        """
        errors = []
        
        # Check for class declaration
        if 'class ' in code and not re.search(r'class\s+\w+', code):
            errors.append("Invalid class declaration")
        
        # Check for method declarations without body (not abstract)
        if re.search(r'(public|private|protected)\s+\w+\s+\w+\s*\([^)]*\)\s*;', code):
            if 'abstract' not in code:
                errors.append("Method declaration without body (not abstract)")
        
        return errors
    
    def _check_csharp_syntax(self, code: str) -> List[str]:
        """
        Check for common C# syntax errors.
        
        Args:
            code: C# code string
            
        Returns:
            List of error messages
        """
        errors = []
        
        # Check for class declaration
        if 'class ' in code and not re.search(r'class\s+\w+', code):
            errors.append("Invalid class declaration")
        
        # Check for method declarations without body (not abstract)
        if re.search(r'(public|private|protected)\s+\w+\s+\w+\s*\([^)]*\)\s*;', code):
            if 'abstract' not in code and 'interface' not in code:
                errors.append("Method declaration without body (not abstract or interface)")
        
        return errors
    
    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported languages.
        
        Returns:
            List[str]: Supported language names
        """
        return self.supported_languages.copy()
