from model_loader import model_loader

def init_model():
    """Initialize the model and load it to GPU"""
    print("Initializing model...")
    pipeline = model_loader.load_model()
    print("Model loaded successfully!")
    return pipeline

if __name__ == "__main__":
    init_model() 