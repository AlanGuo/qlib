#!/bin/bash
# Phase 4.3 长期稳定性测试启动脚本

# 切换到crypto目录的根目录
cd "$(dirname "$0")/.."

# 设置环境变量
export CRYPTO_TEST_DATA_DIR="test_data/stability_test"

echo "Phase 4.3 Long-term Stability Test"
echo "=================================="
echo "Data directory: $CRYPTO_TEST_DATA_DIR"
echo ""

# 创建数据目录
mkdir -p "$CRYPTO_TEST_DATA_DIR"

# 显示测试选项
echo "Select test duration:"
echo "1) Quick test (5 minutes)"
echo "2) Short test (1 hour)"
echo "3) Standard test (24 hours)"
echo "4) Custom duration"
echo ""

read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        duration=0.083
        echo "Running 5-minute quick test..."
        ;;
    2)
        duration=1
        echo "Running 1-hour test..."
        ;;
    3)
        duration=24
        echo "Running 24-hour standard test..."
        ;;
    4)
        read -p "Enter duration in hours: " duration
        echo "Running ${duration}-hour custom test..."
        ;;
    *)
        echo "Invalid choice, using 1-hour test"
        duration=1
        ;;
esac

echo ""
read -p "Run in background? (y/n): " background

if [[ $background == "y" || $background == "Y" ]]; then
    # 后台运行
    echo "Starting test in background..."
    nohup python tests/run_long_term_stability.py --duration $duration > stability_test.out 2>&1 &
    PID=$!
    echo $PID > stability_test.pid
    echo "Test started with PID: $PID"
    echo "Monitor with: tail -f $CRYPTO_TEST_DATA_DIR/logs/stability_test.log"
    echo "Stop with: kill $PID"
    echo "Or use: kill \$(cat stability_test.pid)"
else
    # 前台运行
    echo "Starting test in foreground (Ctrl+C to stop)..."
    python tests/run_long_term_stability.py --duration $duration
fi

echo ""
echo "Test data will be stored in: $CRYPTO_TEST_DATA_DIR"
echo "Logs available at: $CRYPTO_TEST_DATA_DIR/logs/"
echo "Results will be saved to: $CRYPTO_TEST_DATA_DIR/test_results.json"