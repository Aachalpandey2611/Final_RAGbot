from app.services.chunking import AdaptiveChunkingEngine


def test_policy_section_chunking():
    text = """
Section 1: Introduction
This is the intro text.

Section 2: Scope
This section describes scope.

Section 3: Definitions
Definitions here.
"""
    engine = AdaptiveChunkingEngine()
    chunks = engine.chunk(text, doc_type="policy")
    assert len(chunks) == 3
    assert "Introduction" in chunks[0]
    assert "Scope" in chunks[1]


def test_manual_heading_chunking():
    text = """
# Chapter 1: Getting Started
Welcome to the manual.

## Installation
Install steps here.

## Usage
How to use.
"""
    engine = AdaptiveChunkingEngine()
    chunks = engine.chunk(text, doc_type="manual")
    assert any("Getting Started" in c for c in chunks)
    assert any("Installation" in c for c in chunks)
    assert any("Usage" in c for c in chunks)


def test_table_chunking():
    text = """
| Name | Age | City |
|------|-----|------|
| Alice | 30 | NY |
| Bob | 25 | SF |

Some paragraph after table.
"""
    engine = AdaptiveChunkingEngine()
    chunks = engine.chunk(text, doc_type="table")
    assert len(chunks) >= 1
    assert "Alice" in chunks[0]


def test_code_function_chunking():
    text = """
def foo(x):
    return x * 2

def bar(y):
    return y + 1

class Baz:
    def method(self):
        pass
"""
    engine = AdaptiveChunkingEngine()
    chunks = engine.chunk(text, doc_type="code")
    # Expect at least 3 chunks: foo, bar, Baz
    assert any(chunk.strip().startswith("def foo") for chunk in chunks)
    assert any(chunk.strip().startswith("def bar") for chunk in chunks)
    assert any("class Baz" in chunk for chunk in chunks)
