# Python 基础笔记

## 什么是 Python

Python 是一种解释型、面向对象的高级编程语言，由 Guido van Rossum 于 1991 年首次发布。Python 以简洁清晰的语法著称，强调代码可读性。

## 数据类型

### 基本类型
- **int**: 整数，支持任意精度
- **float**: 浮点数，双精度
- **str**: 字符串，不可变序列
- **bool**: 布尔值，True/False
- **None**: 空值

### 容器类型
- **list**: 可变序列 `[1, 2, 3]`
- **tuple**: 不可变序列 `(1, 2, 3)`
- **dict**: 键值对 `{"a": 1, "b": 2}`
- **set**: 无序不重复集合 `{1, 2, 3}`

## 列表推导式

列表推导式是 Python 的特色语法，用于简洁地创建列表：

```python
# 基本形式
squares = [x**2 for x in range(10)]

# 带条件
evens = [x for x in range(20) if x % 2 == 0]

# 嵌套
matrix = [[i*j for j in range(3)] for i in range(3)]
```

## 装饰器

装饰器是一种设计模式，用于在不修改原函数的情况下扩展其功能：

```python
def timer(func):
    import time
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"{func.__name__} 耗时: {time.time() - start:.2f}s")
        return result
    return wrapper

@timer
def slow_function():
    time.sleep(1)
```

## 上下文管理器

使用 `with` 语句自动管理资源：

```python
with open("file.txt", "r") as f:
    content = f.read()
# 文件自动关闭
```
