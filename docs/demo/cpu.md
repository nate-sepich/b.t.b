**Flow Example**:
This document demonstrates the same process described in `C:\Users\Nate\Documents\GitRepo\b.t.b\README.md`, but using CPU as the compute resource instead of GPU. The steps below highlight the time differences and the advantages of using accelerated computing, such as the NVIDIA GeForce GTX 1660 Ti used in this case, which significantly reduces processing time.

1. **Client Interaction**:
    - A user uploads a file named `win_example.png`.
    ```plaintext
    api_service-1      INFO - Received file: win_example.png
    ```

2. **OCR Analysis**:
    - The file is sent to the OCR service for text extraction.
    ```plaintext
    api_service-1      INFO - Sending file to OCR service
    easyocr-1          INFO - File win_example.png read successfully.
    easyocr-1          INFO - File win_example.png successfully converted to numpy array.
    easyocr-1          INFO - Text extraction completed for file win_example.png.
    easyocr-1          INFO - Extracted text: Under 62.5 . Totals WON Result Under 62.5 Mississippi at LSU 10/12/24 6.30 PM Stake Odds Payout (inc Stake) S25.00 -110 547.73 Details
    easyocr-1          INFO - Text extraction time for win_example.png: 1.13 seconds.
    easyocr-1          | INFO:     172.19.0.2:53528 - "POST /ocr HTTP/1.1" 200 OK
    api_service-1      INFO - Received response from OCR service
    api_service-1      INFO - Parsed OCR response into LLMRequestModel
    ```

3. **LLM Processing**:
    - The extracted text is sent to the LLM service for further analysis.
    ```plaintext
    api_service-1      INFO - Sending request to LLM service
    llm_service-1      INFO - Generating content from model
    llm_service-1      INFO - Extracted text: Under 62.5 . Totals WON Result Under 62.5 Mississippi at LSU 10/12/24 6.30 PM Stake Odds Payout (inc Stake) S25.00 -110 547.73 Details
    ollama-1           | [GIN] 2024/10/15 - 20:31:09 | 200 |          2m5s |      172.19.0.7 | POST     "/api/generate"
    llm_service-1      INFO - HTTP Request: POST http://ollama:11434/api/generate "HTTP/1.1 200 OK"
    api_service-1      INFO - Received response from LLM service
    llm_service-1      INFO - Parsed data: [{'bet_id': None, 'result': 'Under 62.5', 'league': 'NCAAF', 'date': '10/12/24 6:30 PM', 'away_team': 'Mississippi', 'home_team': 'LSU', 'wager_team': None, 'bet_type': 'Totals', 'selection': 'Under 62.5', 'odds': '-110', 'stake': '25.00', 'payout': '477.73', 'outcome': 'WON'}]
    api_service-1      INFO - Parsed LLM response into BetDetails models
    llm_service-1      | INFO:     172.19.0.2:49312 - "POST /llm HTTP/1.1" 200 OK
    api_service-1      INFO - Converted BetDetails models to JSON format
    ```

4. **Data Storage**:
    - The structured data is sent to the Storage service.
    ```plaintext
    api_service-1      INFO - Sending parsed data to Storage service
    storage_service-1  Calculated profit/loss for bet b9284fe5-e292-4483-a784-ba23bae11b8f: 22.73
    storage_service-1  Bet b9284fe5-e292-4483-a784-ba23bae11b8f Processed: Under 62.5 - Totals - WON - 22.73
    storage_service-1  | INFO:     172.19.0.2:49214 - "POST /bets HTTP/1.1" 200 OK
    api_service-1      INFO - Successfully stored bets data
    ```

5. **Completion**:
    - The entire process completes in 127 seconds. To see the same results with GPU acceleration, refer to the [README.md](../../README.md) file.
    ```plaintext
    api_service-1      root - INFO - Processing complete in: 126.91432237625122 seconds
    api_service-1      | INFO:     172.19.0.1:34166 - "POST /upload/ HTTP/1.1" 200 OK
    ```

Using the NVIDIA GeForce GTX 1660 Ti, the processing time can be significantly reduced, demonstrating the advantages of accelerated computing over CPU-based processing.

### GPU Results

The following results were obtained using GPU acceleration:

```plaintext
api_service-1      | 2024-10-15 20:58:31,591 - app - INFO - Received file: win_example.png
api_service-1      | 2024-10-15 20:58:31,591 - app - INFO - Sending file to OCR service
easyocr-1          | 2024-10-15 20:58:31,594 - app - INFO - File win_example.png read successfully.
easyocr-1          | 2024-10-15 20:58:31,596 - app - INFO - File win_example.png successfully converted to numpy array.
easyocr-1          | 2024-10-15 20:58:31,814 - app - INFO - Text extraction completed for file win_example.png.
easyocr-1          | 2024-10-15 20:58:31,814 - app - INFO - Extracted text: Under 62.5 . Totals WON Result Under 62.5 Mississippi at LSU 10/12/24 6.30 PM Stake Odds Payout (inc Stake) 525.00 -110 547.73 Details
api_service-1      | 2024-10-15 20:58:31,815 - app - INFO - Received response from OCR service
llm_service-1      | 2024-10-15 20:58:31,817 - INFO - Generating content from model
easyocr-1          | 2024-10-15 20:58:31,814 - app - INFO - Text extraction time for win_example.png: 0.22 seconds.
api_service-1      | 2024-10-15 20:58:31,815 - app - INFO - Parsed OCR response into LLMRequestModel
llm_service-1      | 2024-10-15 20:58:31,817 - INFO - Extracted text: Under 62.5 . Totals WON Result Under 62.5 Mississippi at LSU 10/12/24 6.30 PM Stake Odds Payout (inc Stake) 525.00 -110 547.73 Details
easyocr-1          | INFO:     172.19.0.3:34624 - "POST /ocr HTTP/1.1" 200 OK
api_service-1      | 2024-10-15 20:58:31,815 - app - INFO - Sending request to LLM service
ollama-1           | [GIN] 2024/10/15 - 20:58:44 | 200 | 13.098649266s |      172.19.0.2 | POST     "/api/generate"
llm_service-1      | 2024-10-15 20:58:44,918 - INFO - HTTP Request: POST http://ollama:11434/api/generate "HTTP/1.1 200 OK"
api_service-1      | 2024-10-15 20:58:44,919 - app - INFO - Received response from LLM service
llm_service-1      | 2024-10-15 20:58:44,918 - INFO - Parsed data: [{'bet_id': None, 'result': 'Under 62.5', 'league': 'NCAAF', 'date': '10/12/24 6:30 PM', 'away_team': 'Mississippi', 'home_team': 'LSU', 'wager_team': None, 'bet_type': 'Totals', 'selection': 'Under 62.5', 'odds': '-110', 'stake': '25.00', 'payout': '47.73', 'outcome': 'WON'}]
storage_service-1  | 2024-10-15 20:58:44,922 INFO:Calculated profit/loss for bet 0dda2baf-b39f-4c71-801e-b3688154dac6: 22.72727272727272727272727273
api_service-1      | 2024-10-15 20:58:44,920 - app - INFO - Parsed LLM response into BetDetails models
llm_service-1      | INFO:     172.19.0.3:60052 - "POST /llm HTTP/1.1" 200 OK
api_service-1      | 2024-10-15 20:58:44,920 - app - INFO - Converted BetDetails models to JSON format
api_service-1      | 2024-10-15 20:58:44,920 - app - INFO - Sending parsed data to Storage service
storage_service-1  | 2024-10-15 20:58:44,956 INFO:Bet 0dda2baf-b39f-4c71-801e-b3688154dac6 Processed: Under 62.5 - Totals - WON - 22.72727272727272727272727273
storage_service-1  | INFO:     172.19.0.3:52948 - "POST /bets HTTP/1.1" 200 OK
api_service-1      | 2024-10-15 20:58:44,980 - app - INFO - Successfully stored bets data
api_service-1      | 2024-10-15 20:58:44,981 - root - INFO - Processing complete in: 13.389445543289185 seconds
api_service-1      | INFO:     172.19.0.1:59898 - "POST /upload/ HTTP/1.1" 200 OK
```

### Discussion

#### Time Differences
- **OCR Analysis**:
  - CPU: 1.13 seconds
  - GPU: 0.22 seconds

- **LLM Processing**:
  - CPU: 2 minutes 5 seconds
  - GPU: 13.1 seconds

- **Total Processing Time**:
  - CPU: 127 seconds
  - GPU: 13.39 seconds

#### Advantages of GPU Acceleration
- **Speed**: The GPU significantly reduces the processing time for both OCR and LLM tasks.
- **Efficiency**: Faster processing allows for more tasks to be handled in a shorter time frame.
- **Resource Utilization**: Offloading tasks to the GPU can free up CPU resources for other operations.

Refer to the [README.md](../../README.md) file for more details on GPU acceleration benefits.