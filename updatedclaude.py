
import json
import os
import time
import random
from anthropic import Anthropic
from typing import List, Dict
import logging
import sys

class ClaudeAutomation:
    def __init__(self, api_key: str, json_data: Dict, output_dir: str):
        self.client = Anthropic(api_key=api_key)
        self.problems = json_data['problems']
        self.output_dir = output_dir
        self.failed_retries = {}
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('claude_automation.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logging.info(f"Found {len(self.problems)} problems in the dataset")

    def _generate_prompt(self, problem: Dict, language: str) -> str:
        """Generate a prompt for Claude based on the problem and language."""
        function_signature = problem['function_signatures'][language.lower()]
        
        prompt = f"""Please solve this LeetCode problem #{problem['number']} in {language}.

Title: {problem['title']}
Difficulty: {problem['difficulty']}

Description:
{problem['description']}

Function Signature:
{function_signature}

Examples:"""

        for example in problem['examples']:
            prompt += f"""

Input: {example['input']}
Output: {example['output']}
Explanation: {example['explanation']}"""

        prompt += "\n\nConstraints:\n"
        for constraint in problem['constraints']:
            prompt += f"- {constraint}\n"

        prompt += f"\nProvide a complete, well-commented {language} solution that:"
        prompt += """
1. Handles all edge cases
2. Is optimized for time and space complexity
3. Follows best coding practices
4. Includes comments explaining the approach and complexity analysis
5. Has been tested against the example cases

Please format your response as runnable code without any additional text or markdown formatting."""

        return prompt

    def _save_solution(self, problem_number: int, language: str, solution: str):
        """Save the solution to a file."""
        language_extensions = {
            'python': '.py',
            'java': '.java',
            'cpp': '.cpp'
        }
        
        language_dir = os.path.join(self.output_dir, language.lower())
        os.makedirs(language_dir, exist_ok=True)
        
        file_extension = language_extensions.get(language.lower(), '.txt')
        filename = f"problem_{problem_number}{file_extension}"
        filepath = os.path.join(language_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(solution)
            logging.info(f"Successfully saved solution for problem {problem_number} in {language}")
            return True
        except Exception as e:
            logging.error(f"Error saving solution for problem {problem_number} in {language}: {e}")
            return False

    def _extract_code_from_response(self, response: str, language: str) -> str:
        """Extract the actual code from Claude's response."""
        try:
            code = response.replace('```' + language.lower(), '').replace('```', '')
            cleaned_code = code.strip()
            if not cleaned_code:
                raise ValueError("Empty code response received")
            return cleaned_code
        except Exception as e:
            logging.error(f"Error extracting code from response: {e}")
            raise

    def _make_api_call_with_retry(self, prompt: str, problem_number: int, language: str, max_retries: int = 5) -> str:
        """Make API call with retry logic."""
        for attempt in range(max_retries):
            try:
                logging.info(f"Making API call for problem {problem_number} in {language} (Attempt {attempt + 1}/{max_retries})")
                
                response = self.client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=3000,
                    temperature=0,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                return response.content[0].text
            
            except Exception as e:
                wait_time = (2 ** attempt) + random.uniform(1, 5)
                logging.warning(f"API call failed for problem {problem_number} in {language} (Attempt {attempt + 1}): {str(e)}")
                logging.warning(f"Waiting {wait_time:.2f} seconds before retry...")
                
                if attempt == max_retries - 1:
                    raise
                
                time.sleep(wait_time)

    def generate_solutions(self):
        """Generate solutions for all problems."""
        languages = ['python', 'java', 'cpp']
        successful_solutions = 0
        failed_solutions = []
        
        for problem in self.problems:
            logging.info(f"Processing problem {problem['number']}...")
            
            for language in languages:
                try:
                    logging.info(f"Generating solution for problem {problem['number']} in {language}")
                    
                    # Check if solution already exists
                    language_dir = os.path.join(self.output_dir, language.lower())
                    filename = f"problem_{problem['number']}{'.py' if language=='python' else '.java' if language=='java' else '.cpp'}"
                    filepath = os.path.join(language_dir, filename)
                    
                    if os.path.exists(filepath):
                        logging.info(f"Solution already exists for problem {problem['number']} in {language}, skipping...")
                        successful_solutions += 1
                        continue
                    
                    prompt = self._generate_prompt(problem, language)
                    response_text = self._make_api_call_with_retry(prompt, problem['number'], language)
                    solution = self._extract_code_from_response(response_text, language)
                    
                    if self._save_solution(problem['number'], language, solution):
                        successful_solutions += 1
                    else:
                        failed_solutions.append((problem['number'], language))
                    
                    time.sleep(5)
                    
                except Exception as e:
                    logging.error(f"Failed to process problem {problem['number']} for {language}: {str(e)}")
                    failed_solutions.append((problem['number'], language))
                    time.sleep(10)
                    continue

        # Log final statistics
        logging.info(f"\nProcessing completed:")
        logging.info(f"Successfully generated solutions: {successful_solutions}")
        logging.info(f"Failed solutions: {len(failed_solutions)}")
        if failed_solutions:
            logging.info("Failed problems:")
            for problem_num, lang in failed_solutions:
                logging.info(f"- Problem {problem_num} ({lang})")

def main():
    # Configuration
    api_key = "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"  # Replace with your actual API key
    output_dir = "leetcode_solutions"
    
    # Read JSON data
    try:
        with open('dataset4.json', 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    except Exception as e:
        logging.error(f"Error reading JSON file: {str(e)}")
        raise
    
    # Initialize and run automation
    automation = ClaudeAutomation(api_key, json_data, output_dir)
    automation.generate_solutions()

if __name__ == "__main__":
    main()
