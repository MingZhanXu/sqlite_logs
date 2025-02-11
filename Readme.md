# 使用裝飾器進行try-except，並將log資訊存入SQLite
## SQLite logger 欄位內容
|SQLite欄位名稱|欄位類型|分類|用途|
|-|-|-|-|
|id|Integer|base|排序，方便檢視|
|level|Text|base|當前只有 LOG 以及 ERROR ， LOG 為正常執行，ERROR 為觸發 except，其餘預計增加level有：NOTSET、TRACE、DEBUG、INFO、WARING、CRITICAL|
|timestamp|Text|base|時間戳記，記錄函數執行的時候|
|message|Text|base|log 的訊息|
|system_info|Text|system|包含Computer、CPU、RAM、GPU等資訊|
|host_info|Text|system|設備網路的資訊|
|function_file_name|Text|function|函數所在檔案名稱|
|function_line_number|Text|function|函數所在的行數|
|function_name|Text|function|使用此裝飾器的函數名稱，方便快速閱讀|
|args|Text|function|供使用者查看觸發 LOG 或 ERROR 時的參數|
|kwargs|Text|function|供使用者查慨觸發 LOG 或 ERROR 時的參數|
|return_value|Text|function|使用裝飾器的函數返回值|
|function_time|Real|function|使用裝飾器的函數運行的時長|
|thread_name|Text|thread|執行緒的名稱|
|thread_id|Integer|thread|執行緒的 ID|
|process_id|Integer|thread|行程的 ID|
|tag|Text|extra|logger 的而外標籤|
|extra|Text|extra|logger 的而外訊息|
|exception_type|Text|traceback|函數觸發 except 時的錯誤類型|
|traceback|Text|traceback|觸發 except 時的完整訊息|
## 使用方式
以下為虛擬碼，詳細範例在 sqlite_log.py 內中
```python
if __name__ == "__main__":
    logger_path = 存放log的資料夾
    logger = SQLiteLog(logger_path)

    # 未帶參數的寫法，觸發 except 將會回傳 None
    ##############################################################################################################################################
    @logger.try_except
    def func1():
        pass
    func1()
    # 假設此行為第 10 行，結果將會將 9 存入 logger 中正在寫入的 db 中的 line_number
    ##############################################################################################################################################

    # 帶參數的寫法，觸發 except 將會回傳 error_return 的物件
    ##############################################################################################################################################
    # 傳入 func
    def error_return_func():
        print("error")
    @logger.try_except(error_return=error_return_func())
    def func2():
        raise
    # 結果將會 print 出 error 這個字串

    # 傳入數值
    error_return_value = "error"
    @logger.try_except(error_return=error_return_value)
    def func3():
        raise
    return_value = func3()
    # return_value 內容將會是 "error" 這個字串
    ##############################################################################################################################################
```
