# 使用裝飾器進行try-except，並將log資訊存入SQLite
## SQLite logger 欄位內容
|SQLite欄位名稱|欄位類型|用途|
|-|-|-|
|id|Integer|排序，方便檢視|
|timestamp|Text|時間戳記，記錄函數執行的時候|
|type|Text|只有 LOG 以及 ERROR ， LOG 為正常執行，ERROR 為觸發 except|
|line_number|Integer|使用此裝飾器所被使用的行數，方便追蹤及修改|
|function_name|Text|使用此裝飾器的函數名稱，方便快速閱讀|
|args|Text|供使用者查看觸發 LOG 或 ERROR 時的參數|
|kwargs|Text|供使用者查慨觸發 LOG 或 ERROR 時的參數|
|message|Text|成功執行的回傳數值或觸發 except 時的錯誤|
|function_time|Real|使用此裝飾器函數觸發時執行所消耗的時間|
|traceback|Text|觸發 except 時的完整訊息|
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
