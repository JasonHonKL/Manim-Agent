"""
Math Video AI Agent - Generate Educational Videos with Manim
A Flask application that processes PDF files, extracts mathematical content,
and generates high-quality educational videos using Manim.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import tempfile
import subprocess
import shutil

from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
import PyPDF2
import fitz  # PyMuPDF for better text extraction
import openai
from openai import OpenAI
import re

# Configure enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Config:
    """Application configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    UPLOAD_FOLDER = 'uploads'
    VIDEO_FOLDER = './'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'pdf'}
    OPENAI_API_KEY = "YOUR_API_KEY" 
    MANIM_QUALITY = 'high'  # high, medium, low

class PDFProcessor:
    """Handles PDF processing and content extraction"""
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extract text from PDF using PyMuPDF for better quality"""
        logger.info(f"Starting PDF text extraction from: {file_path}")
        try:
            doc = fitz.open(file_path)
            text = ""
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                text += page_text
                logger.debug(f"Extracted {len(page_text)} characters from page {page_num + 1}")
            doc.close()
            logger.info(f"Successfully extracted {len(text)} characters from PDF")
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF with PyMuPDF: {e}")
            logger.info("Falling back to PyPDF2")
            # Fallback to PyPDF2
            return PDFProcessor._extract_with_pypdf2(file_path)
    
    @staticmethod
    def _extract_with_pypdf2(file_path: str) -> str:
        """Fallback PDF extraction method"""
        logger.info(f"Using PyPDF2 fallback for: {file_path}")
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text += page_text
                    logger.debug(f"PyPDF2: Extracted {len(page_text)} characters from page {page_num + 1}")
                logger.info(f"PyPDF2: Successfully extracted {len(text)} characters")
                return text
        except Exception as e:
            logger.error(f"Error with PyPDF2 extraction: {e}")
            return ""

class ContentAnalyzer:
    """Analyzes PDF content and identifies video-worthy mathematical concepts"""
    
    def __init__(self, api_key: str):
        logger.info("Initializing ContentAnalyzer")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        logger.info("ContentAnalyzer initialized successfully")
        
    
    def analyze_content(self, text: str) -> List[Dict]:
        """Analyze text and extract mathematical concepts suitable for video"""
        logger.info(f"Starting content analysis of {len(text)} characters")
        try:
            prompt = """
            Analyze the following mathematical text and identify concepts that would be suitable for educational videos.
            Look for:
            1. Definitions of mathematical concepts
            2. Theorems and proofs
            3. Worked examples with step-by-step solutions
            4. Geometric constructions
            5. Graph plotting or function visualization
            6. Algorithm demonstrations
            
            For each suitable concept, provide:
            - title: Brief descriptive title
            - type: "definition", "theorem", "example", "construction", "visualization", "algorithm"
            - description: 2-3 sentence description of what the video would show
            - complexity: "basic", "intermediate", "advanced"
            - estimated_duration: estimated video length in seconds
            - key_concepts: list of mathematical concepts involved
            
            Return as JSON array. Maximum 10 items.
            
            Text to analyze:
            """ + text[:4000]  # Limit text length for API
            
            logger.info("Sending content analysis request to OpenAI")
            response = self.client.chat.completions.create(
                model="deepseek/deepseek-r1-0528:free",
                messages=[
                    {"role": "system", "content": "You are an expert mathematics educator who identifies content suitable for educational videos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            logger.info(f"Received response from OpenAI: {len(content)} characters")
            logger.debug(f"OpenAI response preview: {content[:200]}...")
            
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                concepts = json.loads(json_match.group())
                logger.info(f"Successfully parsed {len(concepts)} concepts from response")
                for i, concept in enumerate(concepts):
                    logger.debug(f"Concept {i+1}: {concept.get('title', 'Unknown')} ({concept.get('type', 'Unknown')})")
                return concepts
            else:
                logger.warning("No JSON array found in OpenAI response")
                return []
                
        except Exception as e:
            logger.error(f"Error analyzing content: {e}")
            return []

class ManimVideoGenerator:
    """Generates Manim videos based on mathematical content"""
    
    def __init__(self, api_key: str):
        logger.info("Initializing ManimVideoGenerator")
        self.client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        self.video_folder = Path("videos")
        self.video_folder.mkdir(exist_ok=True)
        logger.info(f"Video folder created/verified: {self.video_folder.absolute()}")
        
        # Check if Manim is available
        self.manim_available = self.check_manim_available()
        logger.info(f"Manim availability check: {self.manim_available}")
    
    def check_manim_available(self) -> bool:
        """Check if Manim is available"""
        logger.info("Checking Manim availability...")
        
        # Try different ways to invoke Manim
        commands_to_try = [
            ['python', '-m', 'manim', '--version'],
            ['manim', '--version'],
            ['python3', '-m', 'manim', '--version']
        ]
        
        for cmd in commands_to_try:
            try:
                logger.info(f"Trying command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    logger.info(f"Manim found! Version info: {result.stdout.strip()}")
                    return True
                else:
                    logger.warning(f"Command failed with return code {result.returncode}: {result.stderr}")
            except FileNotFoundError as e:
                logger.warning(f"Command not found: {' '.join(cmd)} - {e}")
            except subprocess.TimeoutExpired:
                logger.warning(f"Command timed out: {' '.join(cmd)}")
            except Exception as e:
                logger.warning(f"Unexpected error with command {' '.join(cmd)}: {e}")
        
        logger.error("Manim not found in any expected location")
        return False
    
    def generate_manim_code(self, concept: Dict, context: str) -> str:
        """Generate Manim code for a mathematical concept"""
        logger.info(f"Generating Manim code for concept: {concept.get('title', 'Unknown')}")
        logger.debug(f"Concept details: {concept}")
        
        prompt = f"""
        Generate high-quality Manim code for the following mathematical concept:
        
        Title: {concept['title']}
        Type: {concept['type']}
        Description: {concept['description']}
        Complexity: {concept['complexity']}
        Key Concepts: {', '.join(concept.get('key_concepts', []))}
        
        Context from PDF: {context[:1000]}
        
        Requirements:
        1. Create a complete Manim scene class
        2. Use high-quality animations and transitions
        3. Include clear mathematical notation using MathTex
        4. Add explanatory text where appropriate
        5. Use appropriate colors and styling
        6. Include smooth camera movements if needed
        7. Target duration: {concept.get('estimated_duration', 30)} seconds
        
        Return only the Python code for the Manim scene.
        """
        
        try:
            logger.info("Sending Manim code generation request to OpenAI")
            response = self.client.chat.completions.create(
                model="deepseek/deepseek-r1-0528:free",
                messages=[
                    {"role": "system", "content": "You are an expert in creating educational Manim animations. Generate clean, well-commented code."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            
            manim_code = response.choices[0].message.content
            logger.info(f"Generated Manim code: {len(manim_code)} characters")
            logger.debug(f"Manim code preview: {manim_code[:200]}...")
            return manim_code
            
        except Exception as e:
            logger.error(f"Error generating Manim code: {e}")
            return ""
    
    def create_video(self, concept: Dict, context: str) -> Tuple[bool, str, str]:
        """Create video from concept and return success status, video path, and logs"""
        logger.info(f"Starting video creation for concept: {concept.get('title', 'Unknown')}")

        try:
            # Check if Manim is available first
            if not self.manim_available:
                error_msg = "Manim is not installed or not available in PATH"
                logger.error(error_msg)
                return False, "", error_msg

            # Generate Manim code
            logger.info("Step 1: Generating Manim code")
            manim_code = self.generate_manim_code(concept, context)
            if not manim_code:
                error_msg = "Failed to generate Manim code"
                logger.error(error_msg)
                return False, "", error_msg

            logger.info("Step 2: Processing generated code")
            # Clean up code (remove markdown formatting if present)
            original_code_length = len(manim_code)
            if "```python" in manim_code:
                manim_code = manim_code.split("```python")[1].split("```")[0]
                logger.info("Removed python markdown formatting")
            elif "```" in manim_code:
                manim_code = manim_code.split("```")[1].split("```")[0]
                logger.info("Removed generic markdown formatting")

            logger.info(f"Code length after cleanup: {len(manim_code)} (was {original_code_length})")

            # Create temporary file for Manim code
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            scene_name = f"MathScene_{timestamp}"
            temp_file = f"temp_{scene_name}.py"
            temp_path = Path(temp_file).resolve()

            logger.info(f"Step 3: Creating temporary file: {temp_file}")
            logger.info(f"Scene name: {scene_name}")

            # Ensure the code has proper imports and scene class
            if "from manim import *" not in manim_code:
                manim_code = "from manim import *\n\n" + manim_code
                logger.info("Added manim import statement")

            # Write code to file
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(manim_code)
                logger.info(f"Successfully wrote {len(manim_code)} characters to {temp_file}")
            except Exception as e:
                logger.error(f"Failed to write temporary file: {e}")
                return False, "", f"Failed to write temporary file: {e}"

            # Verify file was created
            if not os.path.exists(temp_file):
                error_msg = f"Temporary file {temp_file} was not created"
                logger.error(error_msg)
                return False, "", error_msg

            logger.info(f"Temporary file size: {os.path.getsize(temp_file)} bytes")

            # Run Manim to generate video
            logger.info("Step 4: Running Manim to generate video")

            # Set output directory to the directory of the temp file (i.e., current directory)
            output_dir = temp_path.parent
            logger.info(f"Using output directory: {output_dir}")

            # Commands to try with --media_dir set to output_dir
            commands_to_try = [
                ["python", "-m", "manim", "-qh", "--media_dir", str(output_dir), temp_file, scene_name],
                ["python", "-m", "manim", "-qm", "--media_dir", str(output_dir), temp_file, scene_name],  # medium quality
                ["python", "-m", "manim", "-ql", "--media_dir", str(output_dir), temp_file, scene_name],  # low quality
                ["manim", "-qh", "--media_dir", str(output_dir), temp_file, scene_name],
                ["python3", "-m", "manim", "-qh", "--media_dir", str(output_dir), temp_file, scene_name]
            ]

            result = None
            successful_cmd = None

            for i, cmd in enumerate(commands_to_try):
                try:
                    logger.info(f"Attempt {i+1}: Running command: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

                    logger.info(f"Command return code: {result.returncode}")
                    if result.stdout:
                        logger.info(f"Command stdout: {result.stdout}")
                    if result.stderr:
                        logger.warning(f"Command stderr: {result.stderr}")

                    if result.returncode == 0:
                        successful_cmd = cmd
                        logger.info(f"Command succeeded: {' '.join(cmd)}")
                        break
                    else:
                        logger.warning(f"Command failed with return code {result.returncode}")

                except FileNotFoundError as e:
                    logger.warning(f"Command not found: {' '.join(cmd)} - {e}")
                    continue
                except subprocess.TimeoutExpired:
                    logger.error(f"Command timed out after 300 seconds: {' '.join(cmd)}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error running command {' '.join(cmd)}: {e}")
                    continue

            # Clean up temp file
            logger.info("Step 5: Cleaning up temporary file")
            """
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.info(f"Removed temporary file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary file: {e}")
            """

            if result and result.returncode == 0:
                logger.info("Step 6: Manim execution successful, looking for generated video")

                # Search for video files in the output directory and common Manim subfolders there
                search_directories = [
                    output_dir,
                    output_dir / "videos",
                    output_dir / "videos" / "1080p60",
                    output_dir / "videos" / "720p30",
                    output_dir / "videos" / "480p15",
                    output_dir / "videos" / "854x480p30",
                    output_dir / temp_file.replace('.py', '') / "videos",
                    output_dir / temp_file.replace('.py', '') / "videos" / "1080p60",
                    output_dir / temp_file.replace('.py', '') / "videos" / "720p30",
                    output_dir / temp_file.replace('.py', '') / "videos" / "480p15",
                ]

                found_videos = []
                for search_dir in search_directories:
                    if search_dir.exists():
                        logger.info(f"Searching in directory: {search_dir}")
                        for video_file in search_dir.rglob("*.mp4"):
                            file_age = datetime.now().timestamp() - video_file.stat().st_mtime
                            if file_age < 300:  # 5 minutes
                                found_videos.append(video_file)
                                logger.info(f"Found recent video file: {video_file} (age: {file_age:.1f}s)")

                # Remove duplicates and sort by modification time (newest first)
                found_videos = list(set(found_videos))
                found_videos.sort(key=lambda x: x.stat().st_mtime, reverse=True)

                logger.info(f"Total recent video files found: {len(found_videos)}")

                target_video = None

                # Try to find exact scene name video
                for video in found_videos:
                    if scene_name in video.name or scene_name.lower() in video.name.lower():
                        target_video = video
                        logger.info(f"Found matching scene video: {video}")
                        break

                # If no exact match, pick most recent
                if not target_video and found_videos:
                    target_video = found_videos[0]
                    logger.info(f"Using most recent video: {target_video}")

                if target_video:
                    # Final path is in the same folder as temp_file with scene_name.mp4
                    final_path = output_dir / f"{scene_name}.mp4"

                    try:
                        if target_video != final_path:
                            shutil.copy2(str(target_video), str(final_path))
                            logger.info(f"Copied video from {target_video} to {final_path}")

                        if final_path.exists() and final_path.stat().st_size > 0:
                            logger.info(f"Video generation completed successfully: {final_path}")
                            logger.info(f"Final video size: {final_path.stat().st_size} bytes")
                            return True, str(final_path), "Video generated successfully"
                        else:
                            error_msg = f"Final video file is empty or missing: {final_path}"
                            logger.error(error_msg)
                            return False, "", error_msg

                    except Exception as e:
                        logger.error(f"Failed to copy video file: {e}")
                        if target_video.exists() and target_video.stat().st_size > 0:
                            logger.info(f"Using original video location: {target_video}")
                            return True, str(target_video), "Video generated successfully"
                        else:
                            return False, "", f"Failed to copy video and original is invalid: {e}"
                else:
                    error_msg = "No suitable video file found after generation"
                    logger.error(error_msg)
                    logger.info("Searched directories:")
                    for search_dir in search_directories:
                        if search_dir.exists():
                            logger.info(f"  {search_dir}: {list(search_dir.glob('*'))}")
                    return False, "", error_msg
            else:
                error_msg = f"Manim execution failed. Last error: {result.stderr if result else 'No result'}"
                logger.error(error_msg)
                return False, "", error_msg

        except Exception as e:
            logger.error(f"Unexpected error creating video: {e}", exc_info=True)
            return False, "", str(e)

class MathVideoAgent:
    """Main application class that orchestrates the entire workflow"""
    
    def __init__(self, config: Config):
        logger.info("Initializing MathVideoAgent")
        self.config = config
        self.pdf_processor = PDFProcessor()
        self.content_analyzer = ContentAnalyzer(config.OPENAI_API_KEY)
        self.video_generator = ManimVideoGenerator(config.OPENAI_API_KEY)
        
        # Create directories
        Path(config.UPLOAD_FOLDER).mkdir(exist_ok=True)
        Path(config.VIDEO_FOLDER).mkdir(exist_ok=True)
        
        logger.info(f"Upload folder: {Path(config.UPLOAD_FOLDER).absolute()}")
        logger.info(f"Video folder: {Path(config.VIDEO_FOLDER).absolute()}")
        logger.info("MathVideoAgent initialized successfully")
    
    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        allowed = '.' in filename and filename.rsplit('.', 1)[1].lower() in self.config.ALLOWED_EXTENSIONS
        logger.debug(f"File {filename} allowed: {allowed}")
        return allowed
    
    def process_pdf(self, file_path: str) -> Tuple[bool, str, List[Dict]]:
        """Process PDF and return extracted content and concepts"""
        logger.info(f"Processing PDF: {file_path}")
        try:
            # Extract text
            text = self.pdf_processor.extract_text_from_pdf(file_path)
            if not text.strip():
                logger.error("No text could be extracted from the PDF")
                return False, "No text could be extracted from the PDF", []
            
            logger.info(f"Extracted {len(text)} characters from PDF")
            
            # Analyze content
            concepts = self.content_analyzer.analyze_content(text)
            logger.info(f"Analysis complete: {len(concepts)} concepts identified")
            
            return True, text, concepts
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}", exc_info=True)
            return False, str(e), []

# Flask Application
app = Flask(__name__)
config = Config()
app.config.from_object(config)

# Initialize the agent
logger.info("Starting application initialization")
agent = MathVideoAgent(config)
logger.info("Application initialization complete")

@app.route('/')
def index():
    """Main page"""
    logger.info("Serving main page")
    return render_template('./index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle PDF file upload"""
    logger.info("Upload endpoint called")
    try:
        if 'file' not in request.files:
            logger.warning("No file in request")
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.warning("Empty filename")
            return jsonify({'error': 'No file selected'}), 400
        
        logger.info(f"Processing file: {file.filename}")
        
        if file and agent.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{filename}"
            file_path = os.path.join(config.UPLOAD_FOLDER, filename)
            
            logger.info(f"Saving file to: {file_path}")
            file.save(file_path)
            
            # Verify file was saved
            if os.path.exists(file_path):
                logger.info(f"File saved successfully, size: {os.path.getsize(file_path)} bytes")
            else:
                logger.error("File was not saved successfully")
                return jsonify({'error': 'File save failed'}), 500
            
            # Process PDF
            logger.info("Starting PDF processing")
            success, content, concepts = agent.process_pdf(file_path)
            
            if success:
                # Store in session
                session['pdf_content'] = content
                session['pdf_path'] = file_path
                
                logger.info(f"PDF processed successfully, {len(concepts)} concepts found")
                return jsonify({
                    'success': True,
                    'concepts': concepts,
                    'message': f'Found {len(concepts)} concepts suitable for video generation'
                })
            else:
                logger.error(f"PDF processing failed: {content}")
                return jsonify({'error': content}), 400
        
        logger.warning(f"Invalid file type: {file.filename}")
        return jsonify({'error': 'Invalid file type. Please upload a PDF file.'}), 400
        
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return jsonify({'error': 'Upload failed'}), 500

@app.route('/generate_video', methods=['POST'])
def generate_video():
    """Generate video for selected concept"""
    logger.info("Generate video endpoint called")
    try:
        data = request.get_json()
        concept_index = data.get('concept_index')
        concepts = data.get('concepts', [])
        
        logger.info(f"Request data: concept_index={concept_index}, concepts_count={len(concepts)}")
        
        if concept_index is None or concept_index >= len(concepts):
            logger.warning(f"Invalid concept selection: index={concept_index}, available={len(concepts)}")
            return jsonify({'error': 'Invalid concept selection'}), 400
        
        concept = concepts[concept_index]
        context = session.get('pdf_content', '')
        
        logger.info(f"Selected concept: {concept.get('title', 'Unknown')}")
        logger.info(f"Context length: {len(context)} characters")
        
        # Generate video
        logger.info("Starting video generation")
        success, video_path, message = agent.video_generator.create_video(concept, context)
        
        if success:
            session['current_video'] = {
                'path': video_path,
                'concept': concept,
                'generated_at': datetime.now().isoformat()
            }

            # Return relative URL to video for client to request
            video_url = f"/videos/{os.path.basename(video_path)}"

            logger.info(f"Video generation successful: {video_url}")
            return jsonify({
                'success': True,
                'video_path': video_url,
                'concept': concept,
                'message': message
            })
        else:
            logger.error(f"Video generation failed: {message}")
            return jsonify({'error': message}), 500
            
    except Exception as e:
        logger.error(f"Video generation error: {e}", exc_info=True)
        return jsonify({'error': 'Video generation failed'}), 500

@app.route('/download_video')
def download_video():
    """Download the generated video"""
    logger.info("Download video endpoint called")
    try:
        video_info = session.get('current_video')
        if not video_info:
            logger.warning("No video available for download")
            return jsonify({'error': 'No video available for download'}), 404
        
        video_path = video_info['path']
        logger.info(f"Attempting to download video: {video_path}")
        
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return jsonify({'error': 'Video file not found'}), 404
        
        logger.info(f"Serving video file: {video_path}")
        return send_file(
            video_path,
            as_attachment=True,
            download_name=f"math_video_{video_info['concept']['title'].replace(' ', '_')}.mp4"
        )
        
    except Exception as e:
        logger.error(f"Download error: {e}", exc_info=True)
        return jsonify({'error': 'Download failed'}), 500

@app.route('/videos/<filename>')
def serve_video(filename):
    """Serve video files from the videos directory"""
    logger.info(f"Serving video file: {filename}")
    try:
        video_path = os.path.join(config.VIDEO_FOLDER, filename)
        
        # Security check - ensure the file exists and is in the videos directory
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return jsonify({'error': 'Video file not found'}), 404
        
        # Additional security check - ensure filename doesn't contain path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            logger.warning(f"Invalid filename detected: {filename}")
            return jsonify({'error': 'Invalid filename'}), 400
        
        logger.info(f"Serving video: {video_path}")
        return send_file(
            video_path,
            mimetype='video/mp4',
            as_attachment=False,  # Stream the video instead of downloading
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error serving video {filename}: {e}", exc_info=True)
        return jsonify({'error': 'Failed to serve video'}), 500

@app.route('/ask_question', methods=['POST'])
def ask_question():
    """Handle follow-up questions about the generated video"""
    logger.info("Ask question endpoint called")
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        
        logger.info(f"Question: {question}")
        
        if not question:
            logger.warning("Empty question provided")
            return jsonify({'error': 'Please provide a question'}), 400
        
        video_info = session.get('current_video')
        if not video_info:
            logger.warning("No video context available")
            return jsonify({'error': 'No video context available'}), 404
        
        # Use OpenAI to answer the question
        client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )
        
        context = f"""
        Video concept: {video_info['concept']['title']}
        Description: {video_info['concept']['description']}
        Type: {video_info['concept']['type']}
        Key concepts: {', '.join(video_info['concept'].get('key_concepts', []))}
        
        Original PDF content: {session.get('pdf_content', '')[:1000]}
        """
        
        logger.info("Sending question to OpenAI")
        response = client.chat.completions.create(
            model="deepseek/deepseek-r1-0528:free",
            messages=[
                {"role": "system", "content": "You are a helpful mathematics tutor answering questions about educational videos and mathematical concepts."},
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"}
            ],
            temperature=0.3
        )
        
        answer = response.choices[0].message.content
        logger.info(f"Answer generated: {len(answer)} characters")
        
        return jsonify({
            'success': True,
            'answer': answer,
            'question': question
        })
        
    except Exception as e:
        logger.error(f"Question answering error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to answer question'}), 500

@app.route('/test_manim')
def test_manim():
    """Test endpoint to check if Manim is working"""
    logger.info("Test Manim endpoint called")
    try:
        if hasattr(agent.video_generator, 'manim_available'):
            manim_available = agent.video_generator.manim_available
        else:
            manim_available = agent.video_generator.check_manim_available()
        
        if manim_available:
            # Try to get version info
            try:
                result = subprocess.run(['python', '-m', 'manim', '--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    version_info = result.stdout.strip()
                else:
                    version_info = "Version check failed"
            except:
                version_info = "Could not retrieve version"
            
            logger.info(f"Manim test successful: {version_info}")
            return jsonify({
                'success': True,
                'available': True,
                'version': version_info,
                'message': 'Manim is working correctly'
            })
        else:
            logger.warning("Manim test failed: not available")
            return jsonify({
                'success': False,
                'available': False,
                'message': 'Manim is not available. Please install it first.'
            })
            
    except Exception as e:
        logger.error(f"Manim test error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'available': False,
            'error': str(e),
            'message': 'Error testing Manim'
        })

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=False, host='0.0.0.0', port=5000)