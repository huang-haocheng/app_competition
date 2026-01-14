import json
def to_json(input):
    try:
        return json.dumps({"data":input},ensure_ascii=False)
    
    except TypeError as e:
        raise ValueError(f"无法将输出对象转换为 JSON: {e}")

def from_json(input):
    try:
        return json.loads(input)['data']
    except TypeError as e:
        raise ValueError(f"无法将输出对象转换为 JSON: {e}")    
