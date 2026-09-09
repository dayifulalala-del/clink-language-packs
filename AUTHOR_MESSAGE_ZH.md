# 给作者的说明（修订版）

谢谢你继续改进官方中文输入。我用的是当前能更新到的版本，会补上完整版本号和截图。
我想参与改进中文数据，不只是说候选“不好用”。

我们重新检查了自己的 Community 包，发现上次测试方法确实有问题：
“pin → 万象”这种音节与字数不一致的映射，不能保证被拼音组合器接受；
还同时改了词典和模型。此外，GitHub 两种 Release 查询入口曾返回不同版本。
所以我撤回“已经证明仍使用官方旧表”的结论，旧 commit 4cc48bb 的说法不够严谨。

现在准备了更干净的 zh A/B 测试：完整词典和匹配模型不变，只改 CIME 的一行，
A 为 pin → 拼，B 为 pin → 榀，两者都是合法的一音节一汉字。我们会记录同一手机
上 B → A → B 的候选变化，来证明选中的 Community 数据是否参与。

想请你确认：同码 Community zh 能否接管中文 IME？应该如何选择来源并强制重新加载？
是否只有固定的 zh 才会进入 Pinyin 引擎？CIME 候选还会在哪个阶段被过滤或重排？

修订后的英文说明：
https://github.com/dayifulalala-del/clink-language-packs/blob/main/UPSTREAM_ISSUE.md

说明中的实机结果目前仍是 pending，不应写成已复现的 App bug。
