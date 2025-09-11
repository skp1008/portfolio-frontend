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
        config = self.config
        
        prompt_parts = [config.get("system_prompt", "You are a precise SQL query generator.")]
        
        # Add core rules
        if "core_rules" in config:
            prompt_parts.append("\nCORE RULES:")
            for rule in config["core_rules"]:
                prompt_parts.append(f"• {rule}")
        
        # Add query structure rules
        if "query_structure_rules" in config:
            prompt_parts.append("\nQUERY STRUCTURE RULES:")
            for rule in config["query_structure_rules"]:
                prompt_parts.append(f"• {rule}")
        
        # Add condition rules
        if "condition_rules" in config:
            prompt_parts.append("\nCONDITION RULES:")
            for rule in config["condition_rules"]:
                prompt_parts.append(f"• {rule}")
        
        # Add table-specific rules
        if "table_specific_rules" in config:
            prompt_parts.append("\nTABLE-SPECIFIC RULES:")
            for rule in config["table_specific_rules"]:
                prompt_parts.append(f"• {rule}")
        
        # Add output format
        if "output_format" in config:
            prompt_parts.append("\nOUTPUT FORMAT:")
            output_format = config["output_format"]
            if "sql_query" in output_format:
                prompt_parts.append(f"• {output_format['sql_query']}")
            if "explanation" in output_format:
                prompt_parts.append(f"• {output_format['explanation']}")
        
        # Add error handling
        if "error_handling" in config:
            prompt_parts.append("\nERROR HANDLING:")
            for rule in config["error_handling"]:
                prompt_parts.append(f"• {rule}")
        
        return "\n".join(prompt_parts)
    
    def get_system_prompt(self):
        """Get the complete system prompt."""
        return self.system_prompt
    
    def validate_query(self, query):
        """Validate a SQL query against the MCP rules."""
        issues = []
        
        # Check if query starts with SELECT
        if not query.strip().upper().startswith("SELECT"):
            issues.append("Query doesn't start with SELECT")
        
        # Check if query ends with semicolon
        if not query.strip().endswith(";"):
            issues.append("Query doesn't end with semicolon")
        
        # Check for basic SQL structure
        if "SELECT" in query and "FROM" not in query:
            issues.append("Missing FROM clause")
        
        # Check for common issues
        if "SELECT *" in query and "WHERE" not in query:
            issues.append("Consider adding WHERE clause to limit results")
        
        return issues
    
    def apply_rules(self, user_question, generated_query):
        """Apply MCP rules to refine a generated query."""
        # This is a placeholder for more sophisticated rule application
        # In practice, this would use the LLM to apply the rules
        return generated_query 