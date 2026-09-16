import logging
import json
import os

logger = logging.getLogger(__name__)

class LocalScamClassifier:
    """
    Zero-Latency Trapdoor: Loads the fine-tuned TinyLlama model locally to classify 
    scams instantly without hitting external APIs.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalScamClassifier, cls).__new__(cls)
            cls._instance.model = None
            cls._instance.tokenizer = None
            cls._instance.is_loaded = False
        return cls._instance

    def load_model(self):
        """Loads the model into memory. Call this once on startup."""
        if self.is_loaded:
            return

        model_path = os.path.join(os.path.dirname(__file__), "..", "ai_training", "finetuned_scam_model")
        
        # Check if the user has actually run the training script yet
        if not os.path.exists(model_path):
            logger.warning("Local LLM model not found at %s. Did you run train_llm.py? Skipping local inference.", model_path)
            return

        try:
            logger.info("Loading Local Fine-Tuned Scam Classifier into memory...")
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            # Using CPU or GPU depending on availability
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = AutoModelForCausalLM.from_pretrained(model_path, device_map=device)
            self.is_loaded = True
            logger.info("Local LLM successfully loaded on %s!", device)
        except Exception as e:
            logger.error("Failed to load local LLM: %s", e)

    async def predict_instant_scam(self, transcript: str) -> dict | None:
        """
        Runs inference on the transcript. 
        Returns a dict with 'is_scam' and 'category' if successful, or None if skipped/failed.
        """
        if not self.is_loaded or not self.model or not self.tokenizer:
            return None

        prompt = f"""<|system|>
You are an expert scam detection AI. You extract fake claims and classify phone calls.</s>
<|user|>
Analyze the following phone call transcript and extract scam claims. Output JSON with 'category', 'is_scam' and 'reasoning'.

Transcript: {transcript}</s>
<|assistant|>
"""
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            inputs = self.tokenizer(prompt, return_tensors="pt").to(device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs, 
                    max_new_tokens=100, 
                    temperature=0.1,
                    pad_token_id=self.tokenizer.eos_token_id
                )
                
            response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            
            # Basic parsing of the JSON output
            try:
                # Find JSON bounds if there's extra text
                start_idx = response.find("{")
                end_idx = response.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    json_str = response[start_idx:end_idx+1]
                    result = json.loads(json_str)
                    return result
            except json.JSONDecodeError:
                logger.warning("Local LLM returned malformed JSON: %s", response)
                return None
                
        except Exception as e:
            logger.error("Error during Local LLM inference: %s", e)
            return None
