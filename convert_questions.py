#!/usr/bin/env python3
"""
Script to convert formatted questions from text file to JSON format.
Usage: python convert_questions.py
"""

import json
import re

def convert_questions_to_json(input_file, output_file):
    """
    Convert formatted questions from text file to JSON format.
    
    Expected input format:
    1. Question text...
       - Option 1*
       - Option 2
       - Option 3
    
    Output format:
    [
        {
            "number": 1,
            "text": "Question text...",
            "options": ["Option 1", "Option 2", "Option 3"],
            "correct_answer": 0
        }
    ]
    """
    
    questions = []
    current_question = None
    question_number = 0
    
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found!")
        return []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this is a new question (starts with number and dot)
        question_match = re.match(r'^(\d+)\.\s*(.+)$', line)
        if question_match:
            # Save previous question if exists
            if current_question:
                questions.append(current_question)
            
            # Start new question
            question_number = int(question_match.group(1))
            question_text = question_match.group(2).strip()
            current_question = {
                "number": question_number,
                "text": question_text,
                "options": [],
                "correct_answer": None
            }
            continue
        
        # Check if this is an option (starts with dash)
        option_match = re.match(r'^-\s*(.+)$', line)
        if option_match and current_question:
            option_text = option_match.group(1).strip()
            # Remove asterisk if present and mark as correct answer
            if option_text.endswith('*'):
                option_text = option_text[:-1].strip()
                current_question["correct_answer"] = len(current_question["options"])
            current_question["options"].append(option_text)
    
    # Add the last question
    if current_question:
        questions.append(current_question)
    
    # Write to JSON file
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(questions, file, ensure_ascii=False, indent=3)
        print(f"✅ Successfully converted {len(questions)} questions to {output_file}")
    except Exception as e:
        print(f"❌ Error writing to {output_file}: {e}")
        return []
    
    return questions

def main():
    """Main function to run the conversion"""
    input_file = "formatted_questions.txt"
    output_file = "questions.json"
    
    print("🔄 Converting questions from text to JSON format...")
    print(f"📖 Input file: {input_file}")
    print(f"📄 Output file: {output_file}")
    print("-" * 50)
    
    questions = convert_questions_to_json(input_file, output_file)
    
    if questions:
        print(f"\n📊 Conversion Summary:")
        print(f"   • Total questions: {len(questions)}")
        print(f"   • Questions with correct answers: {sum(1 for q in questions if q['correct_answer'] is not None)}")
        print(f"   • Questions without correct answers: {sum(1 for q in questions if q['correct_answer'] is None)}")
        
        # Show first few questions as example
        print(f"\n📝 First 3 questions preview:")
        for i, q in enumerate(questions[:3]):
            print(f"\n   Question {q['number']}:")
            print(f"   Text: {q['text'][:50]}...")
            print(f"   Options: {len(q['options'])} options")
            print(f"   Correct answer: {q['correct_answer']} ({q['options'][q['correct_answer']] if q['correct_answer'] is not None else 'Not set'})")
        
        print(f"\n✅ Conversion completed successfully!")
        print(f"🎯 You can now run the Flask app with: python app.py")
    else:
        print("❌ Conversion failed!")

if __name__ == "__main__":
    main() 