# Visual Demo

A Streamlit interface is included in `demo/app.py` so reviewers can see the governance flow without reading source code.

## Run

```bash
pip install -r requirements.txt
streamlit run demo/app.py
```

The interface lets a reviewer select a proposed action and tool, provide synthetic evidence IDs, inspect the policy decision and, when required, explicitly approve or reject the action. It then displays a downloadable audit record.

## Safety boundary

The UI is a portfolio demonstration. Execution is simulated. It does not connect to payment, identity, production access-control or employer systems.
