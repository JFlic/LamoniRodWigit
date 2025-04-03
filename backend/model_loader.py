from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import torch

class ModelLoader:
    def __init__(self, model_id="mistralai/Mistral-7B-Instruct-v0.3"):
        self.model_id = model_id
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        
    def load_model(self):
        """Load the model and tokenizer to GPU"""
        print("Loading tokenizer...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        
        print("Loading model to GPU...")
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            device_map="auto",
            load_in_8bit=True
        )
        
        print("Creating text generation pipeline...")
        self.pipeline = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            device_map="auto",
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.95
        )
        
        return self.pipeline

# Create a global instance
model_loader = ModelLoader() 