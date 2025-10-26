"""
Benchmark dataset management for evaluation.

This module provides classes for loading, generating, and managing
benchmark datasets for evaluating context engineering techniques.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json
import random


@dataclass
class TestCase:
    """Single test case for evaluation."""
    
    id: str
    query: str
    ground_truth: Optional[str] = None
    context: str = ""
    category: str = "general"
    difficulty: str = "medium"  # easy, medium, hard
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'query': self.query,
            'ground_truth': self.ground_truth,
            'context': self.context,
            'category': self.category,
            'difficulty': self.difficulty,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestCase":
        """Create TestCase from dictionary."""
        return cls(**data)


class BenchmarkDataset:
    """
    Manages benchmark datasets for evaluation.
    
    Supports loading from files and generating synthetic test cases.
    """
    
    def __init__(self, name: str = "default"):
        """
        Initialize benchmark dataset.
        
        Args:
            name: Name of the dataset
        """
        self.name = name
        self.test_cases: List[TestCase] = []
    
    def add_test_case(self, test_case: TestCase) -> None:
        """Add a test case to the dataset."""
        self.test_cases.append(test_case)
    
    def get_by_category(self, category: str) -> List[TestCase]:
        """Get all test cases for a specific category."""
        return [tc for tc in self.test_cases if tc.category == category]
    
    def get_by_difficulty(self, difficulty: str) -> List[TestCase]:
        """Get all test cases for a specific difficulty."""
        return [tc for tc in self.test_cases if tc.difficulty == difficulty]
    
    def sample(self, n: int, category: Optional[str] = None) -> List[TestCase]:
        """
        Randomly sample n test cases.
        
        Args:
            n: Number of test cases to sample
            category: Optional category filter
            
        Returns:
            List of sampled test cases
        """
        if category:
            pool = self.get_by_category(category)
        else:
            pool = self.test_cases
        
        return random.sample(pool, min(n, len(pool)))
    
    def save(self, filepath: str) -> None:
        """
        Save dataset to JSON file.
        
        Args:
            filepath: Path to save the dataset
        """
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'name': self.name,
            'total_cases': len(self.test_cases),
            'test_cases': [tc.to_dict() for tc in self.test_cases]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, filepath: str) -> "BenchmarkDataset":
        """
        Load dataset from JSON file.
        
        Args:
            filepath: Path to the dataset file
            
        Returns:
            Loaded BenchmarkDataset
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        dataset = cls(name=data.get('name', 'default'))
        for tc_data in data.get('test_cases', []):
            dataset.add_test_case(TestCase.from_dict(tc_data))
        
        return dataset
    
    def __len__(self) -> int:
        """Return number of test cases."""
        return len(self.test_cases)
    
    def __iter__(self):
        """Iterate over test cases."""
        return iter(self.test_cases)


def create_baseline_dataset() -> BenchmarkDataset:
    """
    Create baseline benchmark dataset for Phase 0.
    
    This dataset contains diverse queries across multiple categories
    to establish baseline metrics before any context engineering.
    
    Returns:
        BenchmarkDataset with baseline test cases
    """
    dataset = BenchmarkDataset(name="baseline")
    
    # Technical/Programming questions
    tech_questions = [
        TestCase(
            id="tech_001",
            query="What is the difference between a list and a tuple in Python?",
            ground_truth="Lists are mutable sequences that can be modified after creation, while tuples are immutable sequences that cannot be changed once created. Lists use square brackets [] and tuples use parentheses ().",
            category="technical",
            difficulty="easy"
        ),
        TestCase(
            id="tech_002",
            query="Explain the concept of closures in JavaScript.",
            ground_truth="A closure is a function that has access to variables in its outer (enclosing) lexical scope, even after the outer function has returned. Closures allow functions to maintain access to variables from their creation context.",
            category="technical",
            difficulty="medium"
        ),
        TestCase(
            id="tech_003",
            query="What are the CAP theorem principles in distributed systems?",
            ground_truth="The CAP theorem states that a distributed system can only guarantee two out of three properties: Consistency (all nodes see the same data), Availability (every request receives a response), and Partition tolerance (system continues despite network partitions).",
            category="technical",
            difficulty="hard"
        ),
        TestCase(
            id="tech_004",
            query="How does gradient descent work in machine learning?",
            ground_truth="Gradient descent is an optimization algorithm that iteratively adjusts model parameters to minimize a loss function. It computes the gradient (derivative) of the loss with respect to parameters and moves in the opposite direction of the gradient by a learning rate.",
            category="technical",
            difficulty="medium"
        ),
        TestCase(
            id="tech_005",
            query="What is a race condition in concurrent programming?",
            ground_truth="A race condition occurs when multiple threads or processes access shared data concurrently, and the outcome depends on the unpredictable order of execution. This can lead to inconsistent or incorrect results.",
            category="technical",
            difficulty="medium"
        ),
    ]
    
    # General knowledge questions
    general_questions = [
        TestCase(
            id="gen_001",
            query="What causes seasons on Earth?",
            ground_truth="Seasons are caused by Earth's axial tilt of approximately 23.5 degrees relative to its orbital plane around the Sun. This tilt causes different parts of Earth to receive varying amounts of sunlight throughout the year.",
            category="general",
            difficulty="easy"
        ),
        TestCase(
            id="gen_002",
            query="Who wrote the novel '1984'?",
            ground_truth="George Orwell wrote the dystopian novel '1984', published in 1949.",
            category="general",
            difficulty="easy"
        ),
        TestCase(
            id="gen_003",
            query="What is photosynthesis?",
            ground_truth="Photosynthesis is the process by which plants, algae, and some bacteria convert light energy (usually from the sun) into chemical energy stored in glucose. It uses carbon dioxide and water as inputs and produces glucose and oxygen.",
            category="general",
            difficulty="easy"
        ),
        TestCase(
            id="gen_004",
            query="Explain the water cycle.",
            ground_truth="The water cycle describes the continuous movement of water on, above, and below Earth's surface. It involves evaporation from water bodies, condensation into clouds, precipitation as rain or snow, and collection back into bodies of water.",
            category="general",
            difficulty="medium"
        ),
    ]
    
    # Reasoning questions
    reasoning_questions = [
        TestCase(
            id="reason_001",
            query="If all roses are flowers and some flowers fade quickly, can we conclude that some roses fade quickly?",
            ground_truth="No, we cannot conclude that some roses fade quickly. While all roses are flowers, the statement only tells us that SOME flowers fade quickly, not which specific types. The roses could be among the flowers that don't fade quickly.",
            category="reasoning",
            difficulty="hard"
        ),
        TestCase(
            id="reason_002",
            query="A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?",
            ground_truth="The ball costs $0.05 (5 cents). If the bat costs $1.00 more than the ball, then the bat costs $1.05. Together they equal $1.10.",
            category="reasoning",
            difficulty="medium"
        ),
        TestCase(
            id="reason_003",
            query="If you're running a race and you pass the person in second place, what place are you in?",
            ground_truth="You are in second place. When you pass the person in second place, you take their position, which is second.",
            category="reasoning",
            difficulty="easy"
        ),
    ]
    
    # Factual questions
    factual_questions = [
        TestCase(
            id="fact_001",
            query="What is the capital of Australia?",
            ground_truth="Canberra is the capital of Australia.",
            category="factual",
            difficulty="easy"
        ),
        TestCase(
            id="fact_002",
            query="How many chromosomes do humans have?",
            ground_truth="Humans have 46 chromosomes (23 pairs) in each cell, except for reproductive cells which have 23 chromosomes.",
            category="factual",
            difficulty="medium"
        ),
        TestCase(
            id="fact_003",
            query="When was the United Nations founded?",
            ground_truth="The United Nations was founded on October 24, 1945, after World War II.",
            category="factual",
            difficulty="medium"
        ),
    ]
    
    # Add all questions to dataset
    for question_list in [tech_questions, general_questions, reasoning_questions, factual_questions]:
        for question in question_list:
            dataset.add_test_case(question)
    
    return dataset


def create_rag_dataset() -> BenchmarkDataset:
    """
    Create RAG-specific benchmark dataset for Phase 2+.
    
    These questions are designed to benefit from retrieval-augmented generation.
    
    Returns:
        BenchmarkDataset for RAG evaluation
    """
    dataset = BenchmarkDataset(name="rag")
    
    # Document-dependent questions (will need context)
    rag_questions = [
        TestCase(
            id="rag_001",
            query="According to the project documentation, what is the purpose of Phase 3?",
            category="document_qa",
            difficulty="easy",
            metadata={"requires_context": True}
        ),
        TestCase(
            id="rag_002",
            query="What are the key metrics tracked in the evaluation framework?",
            category="document_qa",
            difficulty="medium",
            metadata={"requires_context": True}
        ),
        TestCase(
            id="rag_003",
            query="Compare the chunking strategies mentioned in the retrieval configuration.",
            category="document_qa",
            difficulty="hard",
            metadata={"requires_context": True, "requires_comparison": True}
        ),
    ]
    
    for question in rag_questions:
        dataset.add_test_case(question)
    
    return dataset

