
import json
import os
import requests
from typing import TypedDict, List
from langgraph.graph import StateGraph
from groq import Groq
from dotenv import load_dotenv
from ..logger_config import get_logger


load_dotenv()

class AnalysisState(TypedDict):
    code: str
    style_issues: List[dict]
    bug_issues: List[dict]
    performance_issues: List[dict]
    next: str
    code_type: str

class CodeAnalyzer:
    def __init__(self):
        self.workflow = self._setup_workflow()
        self.logger = get_logger("code_analyzer.analyzer", "agent.log")
    
    def _make_groq_request(self, prompt: str) -> dict:

        try:
            payload = {
                "model": "llama3-8b-8192",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "response_format": {"type": "json_object"}
            }
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"bearer {os.getenv('GROQ_API_KEY')}",
                    "Content-Type": "application/json"
                },
                data=json.dumps(payload)
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {str(e)}", extra={
                "payload": payload,
                "error_type": type(e).__name__
            })
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse API response: {str(e)}", extra={
                "response_text": response.text,
                "error_type": "JSONDecodeError"
            })
            raise

    def _analyze_code_type(self, state: AnalysisState) -> AnalysisState:

        self.logger.info("Starting code type analysis", extra={"code_length": len(state['code'])})
        
        try:
            prompt = f"""Analyze the following text and determine if it is code or plain text. 
            If it is code, identify the programming language:
            
            {state['code']}
            
            Return a JSON object with the following format:
            {{
                "is_code": <true/false>,
                "language": "<language_name>",
                "reason": "<explanation>"
            }}"""
            
            response = self._make_groq_request(prompt)
            data = response["choices"][0]["message"]["content"]
            result = json.loads(data)
            
            state["code_type"] = result["language"] if result["is_code"] else "text"
            self.logger.info("Code type analysis completed", extra={
                "is_code": result["is_code"],
                "language": result["language"]
            })
        
        except Exception as e:
            self.logger.error(f"Code type analysis failed: {str(e)}", extra={
                "error_type": type(e).__name__
            })
            state["code_type"] = "unknown"
        
        state["next"] = "style_analyzer"
        return state

    def _analyze_style(self, state: AnalysisState) -> AnalysisState:

        self.logger.info("Starting style analysis", extra={"code_type": state["code_type"]})
        
        try:
            if state["code_type"] == "text":
                state["style_issues"] = json.dumps({"issues": []})
                self.logger.info("Skipping style analysis for plain text")
                return state

            prompt = f"""Analyze the following code for style and formatting issues:
            
            {state['code']}
            
            Language: {state['code_type']}
            
            Return a JSON array of issues:
            {{"issues":[{{"type": "style","line": "<line_number>","description": "<description>","suggestion": "<suggestion>"}}]}}"""
            
            response = self._make_groq_request(prompt)
            data = response["choices"][0]["message"]["content"]
            state["style_issues"] = data
            
            issues = json.loads(data).get("issues", [])
            self.logger.info("Style analysis completed", extra={
                "issues_found": len(issues)
            })
        
        except Exception as e:
            self.logger.error(f"Style analysis failed: {str(e)}", extra={
                "error_type": type(e).__name__
            })
            state["style_issues"] = json.dumps({"issues": []})
        
        state["next"] = "bug_analyzer"
        return state

    def _analyze_bugs(self, state: AnalysisState) -> AnalysisState:

        self.logger.info("Starting bug analysis", extra={"code_type": state["code_type"]})
        
        try:
            if state["code_type"] == "text":
                state["bug_issues"] = json.dumps({"issues": []})
                self.logger.info("Skipping bug analysis for plain text")
                return state

            prompt = f"""Analyze the following code for potential bugs and errors:
            
            {state['code']}
            
            Language: {state['code_type']}
            
            Return a JSON array of issues:
            {{"issues":[{{"type": "bug","line": "<line_number>","description": "<description>","suggestion": "<suggestion>"}}]}}"""
            
            response = self._make_groq_request(prompt)
            data = response["choices"][0]["message"]["content"]
            state["bug_issues"] = data
            
            issues = json.loads(data).get("issues", [])
            self.logger.info("Bug analysis completed", extra={
                "issues_found": len(issues)
            })
        
        except Exception as e:
            self.logger.error(f"Bug analysis failed: {str(e)}", extra={
                "error_type": type(e).__name__
            })
            state["bug_issues"] = json.dumps({"issues": []})
        
        state["next"] = "performance_analyzer"
        return state

    def _analyze_performance(self, state: AnalysisState) -> AnalysisState:

        self.logger.info("Starting performance analysis", extra={"code_type": state["code_type"]})
        
        try:
            if state["code_type"] == "text":
                state["performance_issues"] = json.dumps({"issues": []})
                self.logger.info("Skipping performance analysis for plain text")
                return state

            prompt = f"""Analyze the following code for performance improvements:
            
            {state['code']}
            
            Language: {state['code_type']}
            
            Return a JSON array of issues:
            {{"issues":[{{"type": "performance","line": "<line_number>","description": "<description>","suggestion": "<suggestion>"}}]}}"""
            
            response = self._make_groq_request(prompt)
            data = response["choices"][0]["message"]["content"]
            state["performance_issues"] = data
            
            issues = json.loads(data).get("issues", [])
            self.logger.info("Performance analysis completed", extra={
                "issues_found": len(issues)
            })
        
        except Exception as e:
            self.logger.error(f"Performance analysis failed: {str(e)}", extra={
                "error_type": type(e).__name__
            })
            state["performance_issues"] = json.dumps({"issues": []})
        
        state["next"] = "end"
        return state

    def _setup_workflow(self) -> StateGraph:

        workflow = StateGraph(AnalysisState)
        

        workflow.add_node("code_type_analyzer", self._analyze_code_type)
        workflow.add_node("style_analyzer", self._analyze_style)
        workflow.add_node("bug_analyzer", self._analyze_bugs)
        workflow.add_node("performance_analyzer", self._analyze_performance)
        

        workflow.add_edge("code_type_analyzer", "style_analyzer")
        workflow.add_edge("style_analyzer", "bug_analyzer")
        workflow.add_edge("bug_analyzer", "performance_analyzer")
        

        workflow.set_entry_point("code_type_analyzer")
        
        return workflow.compile()

    def analyze_code(self, code: str) -> dict:

        self.logger.info("Starting code analysis", extra={"code_length": len(code)})
        
        try:
            initial_state = {
                "code": code,
                "style_issues": json.dumps({"issues": []}),
                "bug_issues": json.dumps({"issues": []}),
                "performance_issues": json.dumps({"issues": []}),
                "code_type": "text",
                "next": "style_analyzer",
            }
            
            final_state = self.workflow.invoke(initial_state)
            

            all_issues = []
            total_issues = 0
            
            for issue_type in ["style_issues", "bug_issues", "performance_issues"]:
                try:
                    issues = json.loads(final_state[issue_type]).get("issues", [])
                    all_issues.extend(issues)
                    total_issues += len(issues)
                    self.logger.info(f"Processed {issue_type}", extra={
                        "issue_type": issue_type,
                        "issues_found": len(issues)
                    })
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse {issue_type}: {str(e)}", extra={
                        "issue_type": issue_type,
                        "error_type": "JSONDecodeError"
                    })
            
            self.logger.info("Code analysis completed", extra={
                "total_issues": total_issues,
                "code_type": final_state["code_type"]
            })
            
            return {"issues": all_issues}
        
        except Exception as e:
            self.logger.error(f"Code analysis failed: {str(e)}", extra={
                "error_type": type(e).__name__
            })
            return {"issues": [], "error": str(e)}
