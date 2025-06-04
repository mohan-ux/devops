from greetings import greet

def test_greet():
  assert greet("World") == "Hello, World!"
  assert greet("Python") == "Hello, Python!"
  # Add a test for an empty name
  assert greet("") == "Hello, !"
  # Add a test for a name with spaces
  assert greet("Good Morning") == "Hello, Good Morning!"
