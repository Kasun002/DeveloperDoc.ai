"""
Unit tests for Syntax Validator.

Tests the SyntaxValidator class for multiple programming languages including
Python, JavaScript, TypeScript, Java, and C#.
"""

import pytest

from app.agents.syntax_validator import SyntaxValidator


@pytest.fixture
def validator():
    """Create a SyntaxValidator instance."""
    return SyntaxValidator()


def test_validate_python_valid_code(validator):
    """Test validation of valid Python code."""
    code = """
def hello_world():
    print("Hello, World!")
    return True
"""
    result = validator.validate_syntax(code, "Python")
    
    assert result["valid"] is True
    assert len(result["errors"]) == 0
    assert result["language"] == "Python"


def test_validate_python_invalid_syntax(validator):
    """Test validation of invalid Python code."""
    code = """
def broken_function(
    print("Missing closing parenthesis")
"""
    result = validator.validate_syntax(code, "Python")
    
    assert result["valid"] is False
    assert len(result["errors"]) > 0
    assert result["language"] == "Python"


def test_validate_python_indentation_error(validator):
    """Test validation of Python code with indentation error."""
    code = """
def bad_indent():
print("Wrong indentation")
"""
    result = validator.validate_syntax(code, "Python")
    
    assert result["valid"] is False
    assert len(result["errors"]) > 0


def test_validate_javascript_valid_code(validator):
    """Test validation of valid JavaScript code."""
    code = """
function greet(name) {
    console.log("Hello, " + name);
    return true;
}

const arrow = () => {
    return 42;
};
"""
    result = validator.validate_syntax(code, "JavaScript")
    
    assert result["valid"] is True
    assert len(result["errors"]) == 0
    assert result["language"] == "JavaScript"


def test_validate_javascript_unbalanced_braces(validator):
    """Test validation of JavaScript code with unbalanced braces."""
    code = """
function broken() {
    console.log("Missing closing brace");
"""
    result = validator.validate_syntax(code, "JavaScript")
    
    assert result["valid"] is False
    assert len(result["errors"]) > 0
    assert "Unclosed" in result["errors"][0] or "unmatched" in result["errors"][0].lower()


def test_validate_typescript_valid_code(validator):
    """Test validation of valid TypeScript code."""
    code = """
interface User {
    name: string;
    age: number;
}

class UserService {
    getUser(id: number): User {
        return { name: "John", age: 30 };
    }
}
"""
    result = validator.validate_syntax(code, "TypeScript")
    
    assert result["valid"] is True
    assert len(result["errors"]) == 0
    assert result["language"] == "TypeScript"


def test_validate_typescript_unbalanced_brackets(validator):
    """Test validation of TypeScript code with unbalanced brackets."""
    code = """
const arr: number[] = [1, 2, 3;
"""
    result = validator.validate_syntax(code, "TypeScript")
    
    assert result["valid"] is False
    assert len(result["errors"]) > 0


def test_validate_java_valid_code(validator):
    """Test validation of valid Java code."""
    code = """
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
    
    public int add(int a, int b) {
        return a + b;
    }
}
"""
    result = validator.validate_syntax(code, "Java")
    
    assert result["valid"] is True
    assert len(result["errors"]) == 0
    assert result["language"] == "Java"


def test_validate_java_unbalanced_parentheses(validator):
    """Test validation of Java code with unbalanced parentheses."""
    code = """
public class Broken {
    public void method() {
        System.out.println("Missing closing paren";
    }
}
"""
    result = validator.validate_syntax(code, "Java")
    
    assert result["valid"] is False
    assert len(result["errors"]) > 0


def test_validate_csharp_valid_code(validator):
    """Test validation of valid C# code."""
    code = """
public class Program {
    public static void Main(string[] args) {
        Console.WriteLine("Hello, World!");
    }
    
    public int Add(int a, int b) {
        return a + b;
    }
}
"""
    result = validator.validate_syntax(code, "C#")
    
    assert result["valid"] is True
    assert len(result["errors"]) == 0
    assert result["language"] == "C#"


def test_validate_csharp_unbalanced_braces(validator):
    """Test validation of C# code with unbalanced braces."""
    code = """
public class Broken {
    public void Method() {
        Console.WriteLine("Missing closing brace");
    
}
"""
    result = validator.validate_syntax(code, "C#")
    
    assert result["valid"] is False
    assert len(result["errors"]) > 0


def test_validate_empty_code(validator):
    """Test validation of empty code."""
    result = validator.validate_syntax("", "Python")
    
    assert result["valid"] is False
    assert "empty" in result["errors"][0].lower()


def test_validate_whitespace_only(validator):
    """Test validation of whitespace-only code."""
    result = validator.validate_syntax("   \n\n   ", "Python")
    
    assert result["valid"] is False
    assert "empty" in result["errors"][0].lower()


def test_check_balanced_delimiters_nested(validator):
    """Test balanced delimiter checking with nested structures."""
    code = """
def outer():
    def inner():
        return [1, 2, {3: 4}]
    return inner()
"""
    errors = validator._check_balanced_delimiters(code)
    assert len(errors) == 0


def test_check_balanced_delimiters_with_strings(validator):
    """Test that delimiters in strings are ignored."""
    code = """
def test():
    s = "This has ( and { and [ in string"
    return s
"""
    errors = validator._check_balanced_delimiters(code)
    assert len(errors) == 0


def test_check_balanced_delimiters_with_comments(validator):
    """Test that delimiters in comments are ignored."""
    code = """
function test() {
    // This comment has ( and { and [
    /* Multi-line comment with ( and { */
    return true;
}
"""
    errors = validator._check_balanced_delimiters(code)
    assert len(errors) == 0


def test_remove_strings_and_comments(validator):
    """Test removal of strings and comments."""
    code = '''
def test():
    # This is a comment with {
    s = "String with ("
    """Docstring with ["""
    return True
'''
    cleaned = validator._remove_strings_and_comments(code)
    
    # Comments and strings should be removed, but function parentheses remain
    # Check that comment content is removed
    assert "comment with {" not in cleaned
    # Check that string content is removed
    assert "String with (" not in cleaned
    # Check that docstring content is removed
    assert "Docstring with [" not in cleaned


def test_get_supported_languages(validator):
    """Test getting list of supported languages."""
    languages = validator.get_supported_languages()
    
    assert "Python" in languages
    assert "JavaScript" in languages
    assert "TypeScript" in languages
    assert "Java" in languages
    assert "C#" in languages


def test_validate_unknown_language(validator):
    """Test validation of unknown language falls back to basic validation."""
    code = """
function test() {
    return true;
}
"""
    result = validator.validate_syntax(code, "UnknownLang")
    
    # Should perform basic validation (balanced delimiters)
    assert result["valid"] is True
    assert result["language"] == "UnknownLang"


def test_validate_complex_python_code(validator):
    """Test validation of complex Python code with classes and decorators."""
    code = """
from typing import List, Optional

class DataProcessor:
    def __init__(self, data: List[int]):
        self.data = data
    
    @property
    def size(self) -> int:
        return len(self.data)
    
    def process(self) -> Optional[int]:
        if not self.data:
            return None
        return sum(self.data) / len(self.data)
"""
    result = validator.validate_syntax(code, "Python")
    
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_validate_complex_typescript_code(validator):
    """Test validation of complex TypeScript code with generics."""
    code = """
interface Repository<T> {
    findById(id: number): Promise<T | null>;
    save(entity: T): Promise<T>;
}

class UserRepository implements Repository<User> {
    async findById(id: number): Promise<User | null> {
        // Implementation
        return null;
    }
    
    async save(entity: User): Promise<User> {
        // Implementation
        return entity;
    }
}
"""
    result = validator.validate_syntax(code, "TypeScript")
    
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_mismatched_delimiters(validator):
    """Test detection of mismatched delimiters."""
    code = """
def test():
    arr = [1, 2, 3}
"""
    result = validator.validate_syntax(code, "Python")
    
    # Python's ast parser will catch this as a syntax error
    assert result["valid"] is False
    assert len(result["errors"]) > 0
