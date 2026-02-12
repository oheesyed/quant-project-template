Future Additions: 

1. A CLI interface


2. Base ABC class for standardize interface for strategy to expose instead of dataclass and params simple convention


3. /app moved and FastAPI implementation
    
    - Ask chat: Also in the future, would it make sense to expose a strategy as a FastAPI to connect to? Bc currently im 
     thinking that the strategies would simply run on ibkr tws api via runners but im guessing the project repo could be 
     both capable of runners and having FastAPIs for others to plug into and use as well right? 

    - You know now that I am thinking about it, do you think that it would be better to have a main.py with 
     filters for either live or backtest? And just have src (and then later api folder) in app as well as main.py? 

4. Add an example branch that would show an example of how to use the template