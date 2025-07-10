#!/usr/bin/env python3
"""
一键运行所有测试的脚本

这个脚本已经重构，移除了冗余的测试运行步骤，现在只运行各个测试类别一次。
Mock测试已经整合到单元测试中，避免重复运行。

使用方法：
    python run_all_tests.py              # 运行所有测试
    python run_all_tests.py --fast       # 只运行快速测试
    python run_all_tests.py --no-live    # 跳过实时测试
    python run_all_tests.py --summary    # 只显示总结
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

def run_command(command, description, timeout=120):
    """运行命令并返回结果"""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    print(f"执行命令: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        print(f"返回码: {result.returncode}")
        
        if result.stdout:
            print("📄 标准输出:")
            print(result.stdout)
            
        if result.stderr:
            print("⚠️ 错误输出:")
            print(result.stderr)
            
        return result.returncode == 0, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        print(f"⏰ 测试超时 ({timeout}秒)")
        return False, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        print(f"❌ 执行错误: {e}")
        return False, "", str(e)

def setup_environment():
    """设置测试环境"""
    print("🚀 设置测试环境...")
    
    # 确保在正确的目录
    tests_dir = Path(__file__).parent
    os.chdir(tests_dir)
    
    # 设置代理环境变量
    proxy_env = {
        'http_proxy': 'http://127.0.0.1:10808',
        'https_proxy': 'http://127.0.0.1:10808',
        'HTTP_PROXY': 'http://127.0.0.1:10808',
        'HTTPS_PROXY': 'http://127.0.0.1:10808'
    }
    
    for key, value in proxy_env.items():
        os.environ[key] = value
    
    print(f"✅ 当前目录: {os.getcwd()}")
    print(f"✅ 代理设置: {proxy_env['https_proxy']}")

def main():
    parser = argparse.ArgumentParser(description='一键运行所有加密货币数据收集器测试')
    parser.add_argument('--fast', action='store_true', help='只运行快速测试')
    parser.add_argument('--no-live', action='store_true', help='跳过实时测试')
    parser.add_argument('--summary', action='store_true', help='只显示总结')
    args = parser.parse_args()
    
    # 设置环境
    setup_environment()
    
    # 测试结果跟踪
    test_results = []
    start_time = datetime.now()
    
    print(f"\n🎯 开始运行所有测试 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 定义测试套件（移除冗余的mock测试，因为已经整合到单元测试中）
    test_suites = [
        {
            'name': '单元测试',
            'command': 'pytest unit/ -v',
            'description': '运行单元测试（包含整合后的mock测试）',
            'timeout': 180
        },
        {
            'name': '集成测试',
            'command': 'pytest integration/ -v',
            'description': '运行集成测试（组件协作）',
            'timeout': 180
        },
        {
            'name': '性能测试',
            'command': 'pytest performance/ -v -m "not slow"' if args.fast else 'pytest performance/ -v',
            'description': '运行性能测试',
            'timeout': 300
        }
    ]
    
    # 如果不跳过实时测试，添加实时测试
    if not args.no_live:
        test_suites.append({
            'name': '实时测试',
            'command': 'pytest live/ -v --tb=short',
            'description': '运行实时API测试（需要网络代理）',
            'timeout': 600
        })
    
    # 运行测试套件
    for suite in test_suites:
        if args.summary:
            print(f"📋 {suite['name']}: {suite['description']}")
            continue
            
        success, stdout, stderr = run_command(
            suite['command'],
            suite['description'],
            suite['timeout']
        )
        
        test_results.append({
            'name': suite['name'],
            'success': success,
            'stdout': stdout,
            'stderr': stderr
        })
    
    # 如果只是显示总结，直接返回
    if args.summary:
        print("\n📊 使用 --summary 参数只显示测试计划，未实际运行测试")
        return
    
    # 可选：运行综合实时测试（仅在不跳过实时测试时）
    if not args.no_live:
        print(f"\n{'='*60}")
        print("🏃 运行综合实时测试")
        print(f"{'='*60}")
        
        crypto_dir = Path(__file__).parent.parent
        os.chdir(crypto_dir)
        
        comprehensive_test_cmd = 'python tests/runners/run_comprehensive_live_test.py'
        success, stdout, stderr = run_command(
            comprehensive_test_cmd,
            f"运行综合实时测试",
            600
        )
        
        test_results.append({
            'name': "综合实时测试",
            'success': success,
            'stdout': stdout,
            'stderr': stderr
        })
    
    # 生成测试报告
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"\n{'='*60}")
    print("📊 测试总结报告")
    print(f"{'='*60}")
    
    passed = sum(1 for result in test_results if result['success'])
    failed = len(test_results) - passed
    
    print(f"⏱️  总耗时: {duration}")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📈 总计: {len(test_results)}")
    
    print(f"\n📋 详细结果:")
    for result in test_results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"  {status} - {result['name']}")
    
    # 保存测试报告
    os.makedirs("reports", exist_ok=True)
    report_file = f"reports/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"加密货币数据收集器测试报告\n")
        f.write(f"生成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"测试耗时: {duration}\n")
        f.write(f"通过: {passed}, 失败: {failed}, 总计: {len(test_results)}\n\n")
        
        for result in test_results:
            f.write(f"{'='*60}\n")
            f.write(f"测试: {result['name']}\n")
            f.write(f"状态: {'PASS' if result['success'] else 'FAIL'}\n")
            f.write(f"{'='*60}\n")
            if result['stdout']:
                f.write("标准输出:\n")
                f.write(result['stdout'])
                f.write("\n")
            if result['stderr']:
                f.write("错误输出:\n")
                f.write(result['stderr'])
                f.write("\n")
            f.write("\n")
    
    print(f"\n📄 详细报告已保存到: {report_file}")
    
    # 退出码
    if failed > 0:
        print(f"\n❌ 有 {failed} 个测试失败")
        sys.exit(1)
    else:
        print(f"\n🎉 所有测试通过！")
        sys.exit(0)

if __name__ == '__main__':
    main()