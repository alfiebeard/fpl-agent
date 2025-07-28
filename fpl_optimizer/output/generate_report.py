"""
Report generation for FPL Optimizer
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..config import Config


logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates optimization reports"""
    
    def __init__(self, config: Config):
        self.config = config
        self.output_config = config.get_output_config()
        
        # Create output directory if it doesn't exist
        self.output_dir = "reports"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_report(self, report_data: Dict[str, Any]) -> str:
        """Generate a comprehensive optimization report"""
        
        logger.info("Generating optimization report...")
        
        try:
            # Generate different report formats
            report_format = self.output_config.get('report_format', 'html')
            
            if report_format == 'html':
                report_path = self._generate_html_report(report_data)
            elif report_format == 'json':
                report_path = self._generate_json_report(report_data)
            else:
                report_path = self._generate_text_report(report_data)
            
            logger.info(f"Report generated: {report_path}")
            return report_path
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return ""
    
    def _generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML report"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fpl_optimization_report_{timestamp}.html"
        filepath = os.path.join(self.output_dir, filename)
        
        html_content = self._create_html_content(report_data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def _generate_json_report(self, report_data: Dict[str, Any]) -> str:
        """Generate JSON report"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fpl_optimization_report_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        # Convert dataclasses to dict for JSON serialization
        json_data = self._convert_to_json_serializable(report_data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def _generate_text_report(self, report_data: Dict[str, Any]) -> str:
        """Generate text report"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fpl_optimization_report_{timestamp}.txt"
        filepath = os.path.join(self.output_dir, filename)
        
        text_content = self._create_text_content(report_data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        return filepath
    
    def _create_html_content(self, report_data: Dict[str, Any]) -> str:
        """Create HTML content for the report"""
        
        optimization_result = report_data['optimization_result']
        llm_insights = report_data['llm_insights']
        timestamp = report_data['timestamp']
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>FPL Optimization Report</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .header {{
                    background-color: #1e3a8a;
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                }}
                .section {{
                    background-color: white;
                    padding: 20px;
                    margin-bottom: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .section h2 {{
                    color: #1e3a8a;
                    border-bottom: 2px solid #1e3a8a;
                    padding-bottom: 10px;
                }}
                .metric {{
                    display: inline-block;
                    margin: 10px;
                    padding: 15px;
                    background-color: #f8fafc;
                    border-radius: 5px;
                    border-left: 4px solid #1e3a8a;
                }}
                .metric h3 {{
                    margin: 0;
                    color: #1e3a8a;
                }}
                .metric p {{
                    margin: 5px 0 0 0;
                    font-size: 1.2em;
                    font-weight: bold;
                }}
                .transfer {{
                    background-color: #fef3c7;
                    padding: 10px;
                    margin: 5px 0;
                    border-radius: 5px;
                    border-left: 4px solid #f59e0b;
                }}
                .insight {{
                    background-color: #dbeafe;
                    padding: 10px;
                    margin: 5px 0;
                    border-radius: 5px;
                    border-left: 4px solid #3b82f6;
                }}
                .timestamp {{
                    color: #6b7280;
                    font-size: 0.9em;
                    text-align: center;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🧐 FPL Optimization Report</h1>
                <p>Automated Fantasy Premier League Team Optimization</p>
            </div>
            
            <div class="section">
                <h2>📊 Optimization Summary</h2>
                <div class="metric">
                    <h3>Expected Points</h3>
                    <p>{optimization_result.expected_points:.2f}</p>
                </div>
                <div class="metric">
                    <h3>Confidence</h3>
                    <p>{optimization_result.confidence:.1%}</p>
                </div>
                <div class="metric">
                    <h3>Formation</h3>
                    <p>{optimization_result.formation[0]}-{optimization_result.formation[1]}-{optimization_result.formation[2]}</p>
                </div>
            </div>
            
            <div class="section">
                <h2>🔄 Transfers</h2>
        """
        
        if optimization_result.transfers:
            for transfer in optimization_result.transfers:
                html += f"""
                <div class="transfer">
                    <strong>{transfer.player_out.name} ({transfer.player_out.team_name})</strong> 
                    → <strong>{transfer.player_in.name} ({transfer.player_in.team_name})</strong>
                    <br><em>Cost: {transfer.cost} points | Reason: {transfer.reason}</em>
                </div>
                """
        else:
            html += "<p>No transfers recommended</p>"
        
        html += """
            </div>
            
            <div class="section">
                <h2>👑 Captain & Vice Captain</h2>
        """
        
        if optimization_result.captain_id:
            html += f"<p><strong>Captain:</strong> Player ID {optimization_result.captain_id}</p>"
        if optimization_result.vice_captain_id:
            html += f"<p><strong>Vice Captain:</strong> Player ID {optimization_result.vice_captain_id}</p>"
        
        html += """
            </div>
            
            <div class="section">
                <h2>🤖 AI Insights</h2>
        """
        
        if optimization_result.llm_insights:
            html += f"<div class='insight'>{optimization_result.llm_insights.replace(chr(10), '<br>')}</div>"
        else:
            html += "<p>No AI insights available</p>"
        
        html += """
            </div>
            
            <div class="section">
                <h2>📝 Reasoning</h2>
                <p>{optimization_result.reasoning}</p>
            </div>
            
            <div class="timestamp">
                Report generated on {timestamp}
            </div>
        </body>
        </html>
        """.format(timestamp=timestamp)
        
        return html
    
    def _create_text_content(self, report_data: Dict[str, Any]) -> str:
        """Create text content for the report"""
        
        optimization_result = report_data['optimization_result']
        llm_insights = report_data['llm_insights']
        timestamp = report_data['timestamp']
        
        text = f"""
FPL OPTIMIZATION REPORT
=======================

Generated: {timestamp}

OPTIMIZATION SUMMARY
-------------------
Expected Points: {optimization_result.expected_points:.2f}
Confidence: {optimization_result.confidence:.1%}
Formation: {optimization_result.formation[0]}-{optimization_result.formation[1]}-{optimization_result.formation[2]}

TRANSFERS
---------
"""
        
        if optimization_result.transfers:
            for transfer in optimization_result.transfers:
                text += f"""
{transfer.player_out.name} ({transfer.player_out.team_name}) → {transfer.player_in.name} ({transfer.player_in.team_name})
Cost: {transfer.cost} points
Reason: {transfer.reason}
"""
        else:
            text += "No transfers recommended\n"
        
        text += f"""
CAPTAIN & VICE CAPTAIN
---------------------
Captain: Player ID {optimization_result.captain_id or 'Not set'}
Vice Captain: Player ID {optimization_result.vice_captain_id or 'Not set'}

AI INSIGHTS
-----------
{optimization_result.llm_insights or 'No AI insights available'}

REASONING
---------
{optimization_result.reasoning}
"""
        
        return text
    
    def _convert_to_json_serializable(self, obj: Any) -> Any:
        """Convert objects to JSON serializable format"""
        
        if hasattr(obj, '__dict__'):
            return {key: self._convert_to_json_serializable(value) 
                   for key, value in obj.__dict__.items()}
        elif isinstance(obj, list):
            return [self._convert_to_json_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_to_json_serializable(value) 
                   for key, value in obj.items()}
        elif hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat()
        else:
            return obj
