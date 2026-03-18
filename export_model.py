import joblib, json

m = joblib.load('model.pkl')
trees = []
for est in m.estimators_:
    t = est.tree_
    trees.append({
        'children_left': t.children_left.tolist(),
        'children_right': t.children_right.tolist(),
        'feature': t.feature.tolist(),
        'threshold': t.threshold.tolist(),
        'value': t.value.tolist()
    })

with open('model_data.json', 'w') as f:
    json.dump(trees, f)

print('Done! model_data.json created successfully')
print(f'Exported {len(trees)} decision trees')
