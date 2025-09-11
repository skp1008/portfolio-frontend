"""
MCP (Model Context Protocol) Handler

Loads and applies precise instructions to the SQL query generation process.
"""

import json
import re
from pathlib import Path

class MCPHandler:
    def __init__(self, config_file="mcp_instructions.json"):
        self.config = self._load_config(config_file)
        self.system_prompt = self._build_system_prompt()
    
    def _load_config(self, config_file):
        """Load MCP configuration from JSON file."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Warning: MCP config file {config_file} not found. Using default instructions.")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            print(f"⚠️  Warning: Invalid JSON in {config_file}: {e}. Using default instructions.")
            return self._get_default_config()
    
    def _get_default_config(self):
        """Fallback default configuration."""
        return {
            "system_prompt": "You are a precise SQL query generator. Generate EXACTLY what the user asks for.",
            "core_rules": [
                "ONLY implement what is explicitly requested",
                "DO NOT add extra conditions unless specifically asked",
                "ALWAYS start queries with SELECT",
                "Choose the SIMPLEST approach when multiple options exist"
            ]
        }
    
    def _build_system_prompt(self):
        """Build the complete system prompt from configuration."""
        prompt = self.config.get("system_prompt", "")
        prompt += "\n\n"
        
        # Add core rules
        if "core_rules" in self.config:
            prompt += "CORE RULES:\n"
            for rule in self.config["core_rules"]:
                prompt += f"• {rule}\n"
            prompt += "\n"
        
        # Add query structure rules
        if "query_structure_rules" in self.config:
            prompt += "QUERY STRUCTURE RULES:\n"
            for rule in self.config["query_structure_rules"]:
                prompt += f"• {rule}\n"
            prompt += "\n"
        
        # Add condition rules
        if "condition_rules" in self.config:
            prompt += "CONDITION RULES:\n"
            for rule in self.config["condition_rules"]:
                prompt += f"• {rule}\n"
            prompt += "\n"
        
        # Add output format
        if "output_format" in self.config:
            prompt += "OUTPUT FORMAT:\n"
            output_format = self.config["output_format"]
            prompt += f"• {output_format.get('sql_query', 'Provide the complete SQL query first')}\n"
            prompt += f"• {output_format.get('explanation', 'Follow with a brief explanation')}\n"
            prompt += "\n"
        
        # Add validation checklist
        if "validation_checklist" in self.config:
            prompt += "VALIDATION CHECKLIST:\n"
            for item in self.config["validation_checklist"]:
                prompt += f"• {item}\n"
            prompt += "\n"
        

        
        return prompt
    
    def get_system_prompt(self):
        """Get the complete system prompt."""
        return self.system_prompt
    
    def validate_query(self, query):
        """Validate a generated SQL query against the rules."""
        issues = []
        
        # Check if query starts with SELECT
        if not query.strip().upper().startswith("SELECT"):
            issues.append("Query must start with SELECT")
        
        # Check for basic syntax issues
        if not query.strip().endswith(";"):
            issues.append("Query should end with semicolon")
        
        # Check for common SQL syntax patterns
        if "SELECT" in query and "FROM" not in query:
            issues.append("Missing FROM clause")
        
        if "JOIN" in query and "ON" not in query:
            issues.append("JOIN without ON condition")
        
        return issues
    
 