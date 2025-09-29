## Project Purpose

This project explores the iterative development of an **agentic system** for 3D scene creation in Blender. Starting from a simple menu-driven interface (V1), we progressively enhance the agent's capabilities through natural language processing, allowing for use of materials and adding surfaces and curves, and eventually some level of batch operations.

The goal is to demonstrate how agents can evolve from basic reactive systems to more sophisticated and more autonomous tools that understand and execute complex user intentions.

## What We Mean by an 'Agent'

An agent is a system that:
- **Perceives** its environment (receives user commands)
- **Processes** input and determines what to do
- **Executes** actions (generates and runs Blender scripts)
- **Returns** output (feedback, renders, .blend files)

*Note: Each of these steps exists on a spectrum and can vary in capability and level of autonomy. For example, perception can range from simple menu selections to complex natural language understanding, and processing can vary from basic mapping to sophisticated reasoning. This is what we iteratively improve across different versions.*


## Project Evolution

We start with the **simplest form of an agent** in V1—a basic menu-driven system that maps user selections to Blender operations. With each subsequent version, we **iteratively improve the agent** to make it more autonomous, intelligent, and capable:

- **V1**: Basic agent with menu-driven interface and simple object manipulation
- **V2**: Enhanced agent with natural language understanding via OpenAI integration
- **V3**: More advanced agent with ability to add materials, curves, and geometric operations
- **V4**: A more powerful agent with batch processing and multi-object command interpretation


## Directory Structure
Each version (V1, V2, V3, V4) contains its own directory with the source code and README that includes core features (focused on what are new features compared to the previous version) and limitations. 

## Setup Instructions

### Prerequisites
- Python 3.11 or higher
- Blender installed on your system
- OpenAI API key (for V2+)

### Environment Setup with pyenv

1. **Install pyenv** (if not already installed):
   ```bash
   # macOS
   brew install pyenv
  

2. **Install Python version**:
   ```bash
   pyenv install 3.11.9
   ```

3. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

1. **Set Blender path** in `config.py`:
   ```python
   BLENDER_PATH = "/path/to/your/blender"
   ```

2. **Set OpenAI API key** (V2+):
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

### Running the Project

Navigate to the desired version directory and run:
```bash
cd v1  # or v2, v3, v4
python main.py
```