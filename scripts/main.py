from dotenv import load_dotenv

import aws_requests

def main():
    aws_requests.generate_cost_summary()
    pass
if __name__ == '__main__':
    load_dotenv()
    main()