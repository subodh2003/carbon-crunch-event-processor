import concurrent.futures

from processor import process_event


event = {
    "source": "concurrent_test",
    "payload": {
        "metric": "revenue",
        "amount": "100",
        "timestamp": "2026-08-29"
    }
}


def send_event(_):
    return process_event(event)


with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(send_event, range(10)))


for result in results:
    print(result)