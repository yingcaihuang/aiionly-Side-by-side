"""
Main entry point for the Model Comparison System.

This module provides the main function to start the Gradio web application.
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
import gradio as gr
import markdown
import html

from model_comparison_system.config.logging_config import setup_logging, get_logger
from model_comparison_system.config.config_service import ConfigService
from model_comparison_system.api.maas_client import MaasApiClient
from model_comparison_system.services.model_service import ModelService
from model_comparison_system.services.error_service import ErrorHandler
from model_comparison_system.app_controller import AppController
from model_comparison_system.api.models import ModelResponse


class GradioInterface:
    """Gradio web interface for the Model Comparison System."""
    
    def __init__(self, app_controller: AppController):
        """Initialize the Gradio interface."""
        self.app_controller = app_controller
        self.logger = get_logger('gradio_interface')
        
        # Initialize markdown converter with extensions
        self.md = markdown.Markdown(extensions=[
            'fenced_code',
            'tables',
            'nl2br',
            'sane_lists'
        ])
    
    def _render_markdown(self, text: str) -> str:
        """Convert markdown text to HTML.
        
        Args:
            text: Markdown formatted text
            
        Returns:
            HTML formatted text
        """
        if not text:
            return ""
        
        # Reset the markdown converter for fresh conversion
        self.md.reset()
        
        # Convert markdown to HTML
        html_content = self.md.convert(text)
        
        return html_content
        
    def create_interface(self) -> gr.Blocks:
        """Create and configure the Gradio interface with modern design."""
        
        with gr.Blocks(
            title="AI Model Comparison Hub"
        ) as interface:
            
            # Modern header with gradient
            gr.HTML("""
            <div style="text-align: center; padding: 40px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; margin-bottom: 30px; box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);">
                <h1 style="color: white; font-size: 2.5em; margin: 0; font-weight: 700; text-shadow: 0 2px 10px rgba(0,0,0,0.2);">
                    🤖 AI 模型对比中心
                </h1>
                <p style="color: rgba(255,255,255,0.95); font-size: 1.2em; margin-top: 10px; font-weight: 300;">
                    实时并发对比多个 AI 模型的响应结果
                </p>
            </div>
            """)
            
            # Configuration status with modern styling
            with gr.Row():
                config_status = gr.HTML(
                    value='<div style="padding: 12px 20px; background: #f0f9ff; border-left: 4px solid #3b82f6; border-radius: 8px; font-size: 0.95em;">⏳ 正在加载配置...</div>'
                )
            
            # Main input section with modern card design
            with gr.Row():
                with gr.Column(scale=1):
                    gr.HTML("""
                    <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.07); margin-bottom: 20px;">
                        <h3 style="margin: 0 0 16px 0; color: #1f2937; font-size: 1.3em; font-weight: 600;">
                            ✍️ 输入您的提示词
                        </h3>
                    </div>
                    """)
                    
                    prompt_input = gr.Textbox(
                        label="",
                        placeholder="输入任何问题... 例如：'解释量子计算' 或 '写一个 Python 排序函数'",
                        lines=4,
                        max_lines=12,
                        elem_classes="modern-input"
                    )
                    
                    gr.HTML("""
                    <div style="margin-top: 12px; padding: 12px; background: #f9fafb; border-radius: 8px; font-size: 0.9em; color: #6b7280;">
                        💡 <strong>提示：</strong>按 <kbd style="background: white; padding: 2px 6px; border: 1px solid #d1d5db; border-radius: 4px; font-family: monospace;">Ctrl+Enter</kbd> 或 <kbd style="background: white; padding: 2px 6px; border: 1px solid #d1d5db; border-radius: 4px; font-family: monospace;">⌘+Enter</kbd> 提交。支持最多 10,000 字符。
                    </div>
                    """)
                    
                    # Model selection section
                    gr.Markdown("### 🤖 选择对比模型")
                    
                    model_selector = gr.CheckboxGroup(
                        label="",
                        choices=[],  # Will be populated dynamically
                        value=[]     # Will be set to default models
                    )
                    
                    with gr.Row():
                        submit_btn = gr.Button(
                            "🚀 开始对比",
                            variant="primary",
                            size="lg",
                            elem_classes="modern-button"
                        )
            
            # Status section with modern design
            with gr.Row():
                status_text = gr.HTML(
                    value='<div style="padding: 16px 20px; background: #f0fdf4; border-left: 4px solid #10b981; border-radius: 8px; font-size: 1em; font-weight: 500;">✅ 准备就绪，可以开始对比模型</div>'
                )
            
            # Results section with modern card layout
            results_section = gr.Column(visible=False)
            with results_section:
                gr.HTML("""
                <div style="margin: 30px 0 20px 0;">
                    <h2 style="color: #1f2937; font-size: 1.8em; font-weight: 700; margin: 0;">
                        📊 对比结果
                    </h2>
                    <p style="color: #6b7280; margin-top: 8px; font-size: 1em;">
                        所有模型的实时响应结果
                    </p>
                </div>
                """)
                
                # Model responses with modern grid
                responses_display = gr.HTML(
                    label=""
                )
                
                # Metadata display (collapsible)
                with gr.Accordion("📈 详细指标", open=False):
                    metadata_display = gr.JSON(
                        label=""
                    )
            
            # Event handlers
            def update_config_status():
                """Update configuration status display and model selector with modern styling."""
                is_valid, errors = self.app_controller.validate_configuration()
                if is_valid:
                    models = self.app_controller.get_supported_models()
                    config_info = self.app_controller.get_configuration_info()
                    
                    # Get default models from config - use the actual config object
                    try:
                        config = self.app_controller._current_config
                        default_models = config.models.default_models if config else models[:4]
                    except:
                        default_models = models[:4]  # Fallback to first 4 if not set
                    
                    status_html = f"""
                    <div style="padding: 16px 20px; background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); border-left: 4px solid #10b981; border-radius: 10px; box-shadow: 0 2px 8px rgba(16, 185, 129, 0.1);">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span style="font-size: 1.5em;">✅</span>
                            <div style="flex: 1;">
                                <div style="font-weight: 600; color: #065f46; font-size: 1.05em; margin-bottom: 4px;">
                                    配置加载成功
                                </div>
                                <div style="color: #047857; font-size: 0.9em;">
                                    <strong>{len(models)} 个模型可用：</strong> {', '.join(models[:2])}{'...' if len(models) > 2 else ''} | 
                                    <strong>API：</strong> {config_info.get('api_base_url', 'N/A')} | 
                                    <strong>超时：</strong> {config_info.get('timeout', 'N/A')}秒
                                </div>
                            </div>
                        </div>
                    </div>
                    """
                    
                    # Return status HTML and model selector update
                    return status_html, gr.update(choices=models, value=default_models)
                else:
                    error_details = '; '.join(errors)
                    status_html = f"""
                    <div style="padding: 16px 20px; background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); border-left: 4px solid #ef4444; border-radius: 10px; box-shadow: 0 2px 8px rgba(239, 68, 68, 0.1);">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span style="font-size: 1.5em;">❌</span>
                            <div style="flex: 1;">
                                <div style="font-weight: 600; color: #991b1b; font-size: 1.05em; margin-bottom: 4px;">
                                    配置错误
                                </div>
                                <div style="color: #b91c1c; font-size: 0.9em;">
                                    {error_details}
                                </div>
                                <div style="color: #dc2626; font-size: 0.85em; margin-top: 6px;">
                                    💡 请检查 config.yaml 文件，确保所有必需的设置都正确。
                                </div>
                            </div>
                        </div>
                    </div>
                    """
                    return status_html, gr.update(choices=[], value=[])
            
            def submit_prompt_handler(prompt: str, selected_models: List[str]):
                """Handle prompt submission with modern UI updates."""
                # Validate selected models
                if not selected_models:
                    yield (
                        '<div style="padding: 16px 20px; background: #fef2f2; border-left: 4px solid #ef4444; border-radius: 10px;"><span style="font-size: 1.2em;">❌</span> <strong>请至少选择一个模型</strong></div>',
                        gr.update(visible=False),
                        "",
                        gr.update(visible=False)
                    )
                    return
                
                # Enhanced client-side validation
                if not prompt or not prompt.strip():
                    yield (
                        '<div style="padding: 16px 20px; background: #fef2f2; border-left: 4px solid #ef4444; border-radius: 10px;"><span style="font-size: 1.2em;">❌</span> <strong>请输入提示词</strong></div>',
                        gr.update(visible=False),
                        "",
                        gr.update(visible=False)
                    )
                    return
                
                # Check minimum length
                if len(prompt.strip()) < 3:
                    yield (
                        '<div style="padding: 16px 20px; background: #fef2f2; border-left: 4px solid #ef4444; border-radius: 10px;"><span style="font-size: 1.2em;">❌</span> <strong>提示词太短</strong> - 请至少输入 3 个字符</div>',
                        gr.update(visible=False),
                        "",
                        gr.update(visible=False)
                    )
                    return
                
                # Check maximum length
                if len(prompt.strip()) > 10000:
                    char_count = len(prompt.strip())
                    yield (
                        f'<div style="padding: 16px 20px; background: #fef2f2; border-left: 4px solid #ef4444; border-radius: 10px;"><span style="font-size: 1.2em;">❌</span> <strong>提示词太长</strong> - {char_count} 字符（限制：10,000）</div>',
                        gr.update(visible=False),
                        "",
                        gr.update(visible=False)
                    )
                    return
                
                # Initialize streaming state
                streaming_responses = {}
                model_ids = selected_models
                total_models = len(model_ids)
                completed_count = [0]  # Use list to allow modification in callback
                
                # Initialize placeholder responses for all models
                for model_id in model_ids:
                    streaming_responses[model_id] = None
                
                # Show initial state with modern loading indicator
                yield (
                    f'<div style="padding: 16px 20px; background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%); border-left: 4px solid #3b82f6; border-radius: 10px; animation: pulse 2s infinite;"><span style="font-size: 1.2em;">🚀</span> <strong>开始对比</strong> {total_models} 个模型...</div>',
                    gr.update(visible=True),
                    self._format_streaming_html(streaming_responses, prompt, 0, total_models),
                    gr.update(visible=False)
                )
                
                # Define streaming callback
                def streaming_callback(model_id: str, response: ModelResponse):
                    completed_count[0] += 1
                    streaming_responses[model_id] = response
                
                # Run async comparison - use asyncio.run() in a simpler way
                try:
                    result = asyncio.run(
                        self.app_controller.submit_prompt(prompt, streaming_callback, selected_models)
                    )
                except Exception as e:
                    self.logger.error(f"Error in submit_prompt_handler: {e}", exc_info=True)
                    yield (
                        f'<div style="padding: 16px 20px; background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); border-left: 4px solid #ef4444; border-radius: 10px;"><span style="font-size: 1.2em;">❌</span> <strong>错误：</strong> {str(e)}</div>',
                        gr.update(visible=False),
                        "",
                        gr.update(visible=False)
                    )
                    return
                
                if not result or not result['success']:
                    # Modern error display
                    error_msg = result.get('error', '未知错误') if result else '未知错误'
                    icon = "⚙️" if 'configuration' in error_msg.lower() or '配置' in error_msg else "🌐" if 'network' in error_msg.lower() or '网络' in error_msg else "⏱️" if 'timeout' in error_msg.lower() or '超时' in error_msg else "🔐" if 'authentication' in error_msg.lower() or '认证' in error_msg else "❌"
                    
                    yield (
                        f'<div style="padding: 16px 20px; background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); border-left: 4px solid #ef4444; border-radius: 10px;"><span style="font-size: 1.2em;">{icon}</span> <strong>错误：</strong> {error_msg}</div>',
                        gr.update(visible=False),
                        "",
                        gr.update(visible=False)
                    )
                    return
                
                # Format final responses for display
                responses_html = self._format_responses_html(
                    result['responses'],
                    result['metadata']
                )
                
                # Modern success message
                metadata = result['metadata']
                success_count = metadata['success_count']
                error_count = metadata['error_count']
                total_duration = metadata['total_duration']
                
                if error_count == 0:
                    status_msg = f'<div style="padding: 16px 20px; background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); border-left: 4px solid #10b981; border-radius: 10px;"><span style="font-size: 1.2em;">✅</span> <strong>成功！</strong>所有 {success_count} 个模型在 {total_duration:.2f}秒 内响应完成</div>'
                elif success_count == 0:
                    status_msg = f'<div style="padding: 16px 20px; background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); border-left: 4px solid #ef4444; border-radius: 10px;"><span style="font-size: 1.2em;">❌</span> <strong>所有模型失败</strong> - 请查看下方错误详情</div>'
                else:
                    status_msg = f'<div style="padding: 16px 20px; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-left: 4px solid #f59e0b; border-radius: 10px;"><span style="font-size: 1.2em;">⚠️</span> <strong>部分成功：</strong>{success_count} 个成功，{error_count} 个失败（{total_duration:.2f}秒）</div>'
                
                yield (
                    status_msg,
                    gr.update(visible=True),
                    responses_html,
                    gr.update(visible=True)
                )
            
            # Wire up events
            interface.load(
                fn=update_config_status,
                outputs=[config_status, model_selector]
            )
            
            submit_btn.click(
                fn=submit_prompt_handler,
                inputs=[prompt_input, model_selector],
                outputs=[status_text, results_section, responses_display, metadata_display]
            )
            
            # Allow Enter key to submit
            prompt_input.submit(
                fn=submit_prompt_handler,
                inputs=[prompt_input, model_selector],
                outputs=[status_text, results_section, responses_display, metadata_display]
            )
        
        return interface
    
    def _format_responses_html(self, responses: Dict[str, ModelResponse], metadata: Dict[str, Any]) -> str:
        """Format model responses as HTML for display with enhanced error information."""
        if not responses:
            return "<p>No responses to display.</p>"
        
        html_parts = []
        
        # Add responses in modern card grid layout
        html_parts.append('<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 20px; margin-top: 24px;">')
        
        for model_id, response in responses.items():
            is_success = response.error_message is None
            
            # Modern card styling
            if is_success:
                border_color = "#10b981"
                bg_gradient = "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)"
                status_badge = '<span style="background: #10b981; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 600;">✓ 成功</span>'
            else:
                border_color = "#ef4444"
                bg_gradient = "linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%)"
                status_badge = '<span style="background: #ef4444; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 600;">✗ 错误</span>'
            
            # Format duration and timestamp
            duration_text = f"{response.duration:.2f}秒" if response.duration else "N/A"
            timestamp_text = response.timestamp.strftime("%H:%M:%S") if response.timestamp else "N/A"
            
            html_parts.append(f"""
            <div style="background: {bg_gradient}; border: 2px solid {border_color}; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                <div style="background: white; padding: 16px 20px; border-bottom: 2px solid {border_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <h3 style="margin: 0; color: #1f2937; font-size: 1.2em; font-weight: 700;">{model_id}</h3>
                        {status_badge}
                    </div>
                    <div style="display: flex; gap: 16px; font-size: 0.9em; color: #6b7280;">
                        <span><strong>⏱️ 用时：</strong>{duration_text}</span>
                        <span>🕐 {timestamp_text}</span>
                    </div>
                </div>
                <div style="padding: 20px;">
            """)
            
            if response.error_message:
                # Error display
                error_html = html.escape(response.error_message)
                html_parts.append(f"""
                <div style="background: white; padding: 16px; border-radius: 10px; border-left: 4px solid #ef4444;">
                    <div style="color: #dc2626; line-height: 1.7; font-size: 0.95em;">{error_html}</div>
                </div>
                """)
            else:
                # Success content display with markdown
                rendered_content = self._render_markdown(response.content) if response.content else "No content"
                html_parts.append(f"""
                <div class="model-response" style="background: white; padding: 20px; border-radius: 10px; line-height: 1.7; color: #374151; font-size: 0.95em;">
                    {rendered_content}
                </div>
                """)
            
            html_parts.append('</div></div>')
        
        html_parts.append('</div>')
        
        return ''.join(html_parts)
    
    def _format_streaming_html(self, responses: Dict[str, Optional[ModelResponse]], prompt: str, completed: int, total: int) -> str:
        """Format streaming model responses as HTML for real-time display."""
        html_parts = []
        
        # Add summary header with modern styling
        html_parts.append(f"""
        <div style="background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%); padding: 16px 20px; border-radius: 12px; margin-bottom: 20px; border-left: 4px solid #3b82f6;">
            <h3 style="margin: 0 0 12px 0; color: #1e40af; font-size: 1.2em;">📋 对比进行中</h3>
            <p style="margin: 0 0 8px 0; color: #1e3a8a;"><strong>提示词：</strong> {prompt[:200]}{'...' if len(prompt) > 200 else ''}</p>
            <p style="margin: 0; color: #1e3a8a;"><strong>进度：</strong> {completed}/{total} 个模型已完成</p>
        </div>
        """)
        
        # Add responses in modern grid layout
        html_parts.append('<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 20px;">')
        
        for model_id, response in responses.items():
            if response is None:
                # Model is still pending - modern loading state
                html_parts.append(f"""
                <div style="background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%); border: 2px solid #d1d5db; border-radius: 16px; padding: 0; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                    <!-- Card Header -->
                    <div style="background: white; padding: 16px 20px; border-bottom: 2px solid #d1d5db;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="margin: 0; color: #1f2937; font-size: 1.2em; font-weight: 700;">
                                {model_id}
                            </h3>
                            <span style="background: #f59e0b; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 600;">⏳ 等待中</span>
                        </div>
                    </div>
                    
                    <!-- Card Body -->
                    <div style="padding: 20px;">
                        <div style="color: #6b7280; font-style: italic; text-align: center; padding: 20px;">
                            等待响应...
                        </div>
                    </div>
                </div>
                """)
            else:
                # Model has completed - modern success/error state
                is_success = response.error_message is None
                
                if is_success:
                    border_color = "#10b981"
                    bg_gradient = "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)"
                    status_badge = '<span style="background: #10b981; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 600;">✓ 成功</span>'
                else:
                    border_color = "#ef4444"
                    bg_gradient = "linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%)"
                    status_badge = '<span style="background: #ef4444; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 600;">✗ 错误</span>'
                
                duration_text = f"{response.duration:.2f}秒" if response.duration else "N/A"
                timestamp_text = response.timestamp.strftime("%H:%M:%S") if response.timestamp else "N/A"
                
                html_parts.append(f"""
                <div style="background: {bg_gradient}; border: 2px solid {border_color}; border-radius: 16px; padding: 0; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                    <!-- Card Header -->
                    <div style="background: white; padding: 16px 20px; border-bottom: 2px solid {border_color};">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <h3 style="margin: 0; color: #1f2937; font-size: 1.2em; font-weight: 700;">
                                {model_id}
                            </h3>
                            {status_badge}
                        </div>
                        <div style="display: flex; gap: 16px; font-size: 0.9em; color: #6b7280;">
                            <span><strong>⏱️ 用时：</strong>{duration_text}</span>
                            <span>🕐 {timestamp_text}</span>
                        </div>
                    </div>
                    
                    <!-- Card Body -->
                    <div style="padding: 20px;">
                """)
                
                if response.error_message:
                    html_parts.append(f"""
                    <div style="background: white; padding: 16px; border-radius: 10px; border-left: 4px solid #ef4444;">
                        <div style="color: #dc2626; line-height: 1.7; font-size: 0.95em;">
                            {response.error_message}
                        </div>
                    </div>
                    """)
                else:
                    rendered_content = self._render_markdown(response.content) if response.content else "No content"
                    html_parts.append(f"""
                    <div style="background: white; padding: 20px; border-radius: 10px; line-height: 1.7; color: #374151; font-size: 0.95em;">
                        {rendered_content}
                    </div>
                    """)
                
                html_parts.append('</div></div>')  # Close card body and card
        
        html_parts.append('</div>')
        
        return ''.join(html_parts)


def main(config_path: Optional[str] = None) -> None:
    """
    Main entry point for the Model Comparison System.
    
    Args:
        config_path: Optional path to configuration file
    """
    # Set default config path
    if config_path is None:
        config_path = "config.yaml"
    
    # Check if config file exists
    config_file = Path(config_path)
    if not config_file.exists():
        print(f"Error: Configuration file '{config_path}' not found.")
        print("Please create a config.yaml file or specify a valid config path.")
        sys.exit(1)
    
    # Setup logging
    basic_logging_config = {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    }
    setup_logging(basic_logging_config)
    
    logger = get_logger('main')
    logger.info("Starting Model Comparison System...")
    
    try:
        # Initialize services
        config_service = ConfigService(config_path)
        
        # Validate configuration first
        config = config_service.load_config()
        errors = config_service.validate_config(config)
        if errors:
            logger.error(f"Configuration validation failed: {errors}")
            print(f"Configuration errors: {'; '.join(errors)}")
            sys.exit(1)
        
        # Initialize API client and services
        api_client = MaasApiClient(
            base_url=config.api.base_url,
            api_key=config.api.api_key,
            timeout=config.api.timeout
        )
        
        error_handler = ErrorHandler(logger)
        model_service = ModelService(api_client, config, error_handler)
        app_controller = AppController(config_service, model_service)
        
        # Create and launch Gradio interface
        gradio_interface = GradioInterface(app_controller)
        interface = gradio_interface.create_interface()
        
        logger.info("Model Comparison System started successfully")
        print("🚀 Model Comparison System is starting...")
        print(f"📁 Using configuration: {config_path}")
        print(f"🌐 Models available: {', '.join(config.models.supported_models)}")
        
        # Launch the interface with Gradio 6.0 compatible parameters and modern styling
        interface.launch(
            server_name="127.0.0.1",
            server_port=7860,
            share=False,
            show_error=True,
            quiet=False,
            theme=gr.themes.Soft(
                primary_hue="blue",
                secondary_hue="purple",
                neutral_hue="slate",
                font=["Inter", "system-ui", "sans-serif"]
            ),
            css="""
            /* Modern card animations */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.8; }
            }
            
            /* Global improvements */
            .gradio-container {
                max-width: 1400px !important;
                margin: auto !important;
            }
            
            /* Modern input styling */
            .modern-input textarea {
                border: 2px solid #e5e7eb !important;
                border-radius: 12px !important;
                padding: 16px !important;
                font-size: 1em !important;
                transition: all 0.2s !important;
            }
            
            .modern-input textarea:focus {
                border-color: #3b82f6 !important;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
            }
            
            /* Modern button styling */
            .modern-button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
                border: none !important;
                border-radius: 12px !important;
                padding: 16px 32px !important;
                font-size: 1.1em !important;
                font-weight: 600 !important;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4) !important;
                transition: all 0.3s !important;
            }
            
            .modern-button:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5) !important;
            }
            
            /* Markdown rendering styles */
            .model-response h1, .model-response h2, .model-response h3, 
            .model-response h4, .model-response h5, .model-response h6 {
                margin-top: 20px;
                margin-bottom: 12px;
                font-weight: 700;
                line-height: 1.3;
                color: #1f2937;
            }
            
            .model-response h1 { font-size: 1.9em; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; }
            .model-response h2 { font-size: 1.6em; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px; }
            .model-response h3 { font-size: 1.3em; }
            .model-response h4 { font-size: 1.1em; }
            
            .model-response p {
                margin-bottom: 14px;
                line-height: 1.8;
                color: #374151;
            }
            
            .model-response ul, .model-response ol {
                margin-left: 24px;
                margin-bottom: 14px;
                line-height: 1.8;
            }
            
            .model-response li {
                margin-bottom: 6px;
                color: #374151;
            }
            
            .model-response code {
                background-color: #f3f4f6;
                padding: 3px 8px;
                border-radius: 4px;
                font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
                font-size: 0.9em;
                color: #dc2626;
                border: 1px solid #e5e7eb;
            }
            
            .model-response pre {
                background-color: #1f2937;
                color: #f9fafb;
                padding: 16px;
                border-radius: 10px;
                overflow-x: auto;
                margin-bottom: 16px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            
            .model-response pre code {
                background-color: transparent;
                padding: 0;
                color: #f9fafb;
                font-size: 0.9em;
                border: none;
            }
            
            .model-response blockquote {
                border-left: 4px solid #3b82f6;
                padding-left: 16px;
                margin-left: 0;
                margin-bottom: 16px;
                color: #4b5563;
                font-style: italic;
                background: #f9fafb;
                padding: 12px 16px;
                border-radius: 4px;
            }
            
            .model-response table {
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 16px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                border-radius: 8px;
                overflow: hidden;
            }
            
            .model-response table th,
            .model-response table td {
                border: 1px solid #e5e7eb;
                padding: 12px 16px;
                text-align: left;
            }
            
            .model-response table th {
                background-color: #f3f4f6;
                font-weight: 700;
                color: #1f2937;
            }
            
            .model-response table tr:nth-child(even) {
                background-color: #f9fafb;
            }
            
            .model-response table tr:hover {
                background-color: #f3f4f6;
            }
            
            .model-response a {
                color: #3b82f6;
                text-decoration: none;
                font-weight: 500;
                transition: color 0.2s;
            }
            
            .model-response a:hover {
                color: #2563eb;
                text-decoration: underline;
            }
            
            .model-response hr {
                border: none;
                border-top: 2px solid #e5e7eb;
                margin: 24px 0;
            }
            
            .model-response strong {
                font-weight: 700;
                color: #1f2937;
            }
            
            .model-response em {
                font-style: italic;
                color: #4b5563;
            }
            
            /* Smooth animations */
            .model-response {
                animation: fadeIn 0.4s ease-out;
            }
            """
        )
        
    except Exception as e:
        logger.error(f"Failed to start Model Comparison System: {e}", exc_info=True)
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()