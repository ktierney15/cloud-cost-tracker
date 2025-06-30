from dotenv import load_dotenv
import json

import aws_requests

def main():
    aws_cost_data = aws_requests.generate_cost_summary()
    print(json.dumps(aws_cost_data, indent=4))
    pass
if __name__ == '__main__':
    load_dotenv()
    main()