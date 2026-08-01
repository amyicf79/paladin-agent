"""
v1.0.2 — 策略优化器叶片
职责：加载经验库，分析工具生成的成功/失败模式，产出策略洞察。
零依赖，纯标准库。
"""

import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict

# v1.2: 语义检索增强
from semantic_search import get_engine
# v1.3: 小世界拓扑分析
from experience_graph import get_graph
from cognitive_zone import get_classifier
from dual_path import get_recommender
from metacognition_gate import MetacognitionGate, get_gate
from entropy_budget import EntropyBudget, get_budget
from agent_registry import get_registry
from multi_agent_arbiter import get_arbiter
from market_scheduler import get_scheduler


@dataclass
class StrategyInsight:
    """单条策略洞察"""
    category: str  # "naming" | "parameter" | "pattern" | "gap"
    title: str
    description: str
    evidence: List[str]  # 支撑证据（经验条目 key）
    recommendation: str


@dataclass
class StrategyReport:
    """策略报告"""
    summary: str
    total_experiences: int
    insights: List[StrategyInsight] = field(default_factory=list)
    tool_count: int = 0
    success_rate: float = 1.0


class StrategyOptimizer:
    """策略优化器：从经验数据中提炼模式，优化生成策略"""

    def __init__(self, store_path: Optional[str] = None):
        if store_path is None:
            base = os.path.dirname(os.path.abspath(__file__))
            store_path = os.path.join(base, "experience_store")
        self.store_path = store_path

    def load_experiences(self) -> List[Dict[str, Any]]:
        """加载所有经验记录"""
        if not os.path.isdir(self.store_path):
            return []
        experiences = []
        for f in os.listdir(self.store_path):
            if not f.endswith('.json') or f == "index.json":
                continue
            fp = os.path.join(self.store_path, f)
            with open(fp, 'r', encoding='utf-8') as fh:
                experiences.append(json.load(fh))
        return experiences

    def analyze(self) -> StrategyReport:
        """分析经验数据，生成策略报告"""
        exps = self.load_experiences()
        if not exps:

            return StrategyReport(summary="经验库为空，无法分析", total_experiences=0)

        tools = set(e.get("tool_name") or e.get("tool", "") for e in exps)
        success = sum(1 for e in exps if e.get("success"))
        insights = []

        # 2) 动作类型分析（I2新增）
        actions = set(e.get("action") for e in exps if e.get("action"))
        if actions:
            insights.append(StrategyInsight(
                category="action_coverage",
                title="动作类型覆盖",
                description=f"已覆盖 {len(actions)} 种动作类型: {', '.join(sorted(actions))}",
                evidence=[f"{a}: {sum(1 for e in exps if e.get('action')==a)}次" for a in sorted(actions)],
                recommendation="继续补全新动作类型"
            ))
        else:
            insights.append(StrategyInsight(
                category="action_coverage",
                title="动作类型覆盖",
                description="经验库未记录action类型，需I1补全后重新生成",
                evidence=[],
                recommendation="运行 paladin run 创建新工具触发经验记录"
            ))

        # 3) 工具总数统计
        insights.append(StrategyInsight(
            category="tool_count",
            title="工具总数",
            description=f"共计 {len(tools)} 个工具",
            evidence=[f"工具: {t}" for t in sorted(tools)],
            recommendation="工具数不足时优先补全基础工具类型"
        ))

        # 1) 命名模式分析
        names = [e.get("tool_name", "") for e in exps]
        prefix_counter = Counter(n.split("_")[0] for n in names if "_" in n)
        if prefix_counter:
            common = prefix_counter.most_common(1)[0]
            insights.append(StrategyInsight(
                category="naming",
                title="命名词偏好",
                description=f"工具名最常用前缀: '{common[0]}'（出现 {common[1]} 次）",
                evidence=[n for n in names if n.startswith(common[0])],
                recommendation="codegen 模板的无参数函数名可优先使用此模式"
            ))

        # 2) 错误类型分析
        errors = [e.get("error_type", "Passed") for e in exps]
        error_counts = Counter(errors)
        for err_type, count in error_counts.most_common(3):
            insights.append(StrategyInsight(
                category="pattern",
                title=f"错误类型: {err_type}",
                description=f"出现 {count}/{len(exps)} 次 ({count*100//len(exps)}%)",
                evidence=[e.get("tool_name", "") for e in exps if e.get("error_type") == err_type],
                recommendation="检查该错误类型对应的验证规则是否过于严格"
            ))

        # 3) 参数模式分析
        param_tools = [e.get("tool_name", "") for e in exps]
        has_underscore = sum(1 for n in param_tools if "_" in n)
        insights.append(StrategyInsight(
            category="parameter",
            title="命名风格",
            description=f"下划线命名占比: {has_underscore}/{len(param_tools)} ({has_underscore*100//max(len(param_tools),1)}%)",
            evidence=param_tools[:3],
            recommendation="当前 100% 使用 snake_case，与 Python 社区规范一致"
        ))

        # 4) 覆盖缺口分析
        expected = {"extract", "read", "search", "list", "check", "format", "generate", "parse"}
        covered = set(n.split("_")[0] for n in names if "_" in n)
        missing = expected - covered
        if missing:
            insights.append(StrategyInsight(
                category="gap",
                title="场景缺口",
                description=f"未覆盖的动作类型: {', '.join(missing)}",
                evidence=list(missing),
                recommendation="codegen 模板可预置这些场景的参数模板"
            ))

        # v1.2: 语义检索增强分析
        try:
            engine = get_engine()
            if not engine._index_built:
                engine.build_index(self.store_path)
            ss_stats = engine.get_stats()
            insights.append(StrategyInsight(
                category="semantic",
                title="语义检索能力",
                description=f"字n-gram TF-IDF引擎 | {ss_stats['doc_count']}条已索引 | 词汇量{ss_stats['vocab_size']}",
                evidence=[f"引擎: char_ngram_tfidf v{ss_stats.get('version','?')}"],
                recommendation="经验库越丰富，语义检索越精准"
            ))
            # 覆盖率分析：按相似度聚类
            all_results = []
            for e in exps:
                q = f"{e.get('tool_name','')} {e.get('error_type','')}"
                hits = engine.search(q, top_k=3)
                all_results.append(hits)
            avg_hits = sum(len(h) for h in all_results) / max(len(all_results), 1)
            insights.append(StrategyInsight(
                category="coverage",
                title="语义覆盖密度",
                description=f"平均每条经验可召回 {avg_hits:.1f} 条语义相关经验",
                evidence=[f"总经验数: {len(exps)}"],
                recommendation="经验库交叉引用密度越高，优化效果越好"
            ))
        except Exception as e:
            pass
        
        # v1.3: 小世界拓扑洞察
        try:
            graph = get_graph()
            if not graph._built:
                graph.build(self.store_path)
            gs = graph.get_stats()
            if gs.get("built"):
                insights.append(StrategyInsight(
                    category="topology",
                    title="小世界网络结构",
                    description=f"{gs['nodes']}节点 {gs['edges']}边 {gs['community_count']}社区 | "
                                f"捷径{gs['shortcuts']}条({gs['shortcut_ratio']:.1%}) | "
                                f"聚类系数{gs['avg_clustering']}",
                    evidence=[
                        f"平均度: {gs['avg_degree']}",
                        f"边密度: {gs['edge_density']}",
                        f"捷径占比: {gs['shortcut_ratio']:.1%}",
                    ],
                    recommendation="捷径比例<5%说明跨模块连接不足，可增加混合任务经验"
                ))
                # 各社区工具分布
                cs = graph.get_community_stats()
                if cs.get("community_count", 0) <= len(gs.get("community_sizes", {})):
                    # 列出混合社区（多工具类型）
                    mixed = []
                    for cid, tools in cs.get("community_tools", {}).items():
                        if len(tools) >= 2:
                            mixed.append(f"社区{cid}({','.join(tools)})")
                    if mixed:
                        insights.append(StrategyInsight(
                            category="community",
                            title="跨功能社区（潜在通用经验）",
                            description=" | ".join(mixed),
                            evidence=["这些社区包含多种工具，经验可交叉复用"],
                            recommendation="跨功能社区的经验具有更高通用性，推荐优先复用"
                        ))
        except Exception:
            pass
        
        # v1.4: 认知分区洞察
        try:
            classifier = get_classifier()
            zone_stats = classifier.get_zone_stats(self.store_path)
            zd = zone_stats.get("zone_distribution", {})
            prof = zd.get("proficient", {}).get("pct", 0)
            perp = zd.get("perplexed", {}).get("pct", 0)
            miss = zd.get("missing", {}).get("pct", 0)
            total = zone_stats.get("total_queries", 0)
            insights.append(StrategyInsight(
                category="competence",
                title=f"能力圈分布: 熟练{prof:.0f}% 困惑{perp:.0f}% 缺失{miss:.0f}%",
                description=f"{total}条经验中 {zd.get('proficient',{}).get('count',0)}条可熟练执行, "
                            f"{zd.get('perplexed',{}).get('count',0)}条需验证",
                evidence=["熟练区: 直接执行无需检索", "困惑区: 检索+验证后执行"],
                recommendation="增加困惑区经验的覆盖率阈值" if perp > 50 else "能力圈结构合理"
            ))
            prof_tools = [d['tool'] for d in zone_stats.get('zone_details', {}).get('proficient', [])]
            if prof_tools:
                insights.append(StrategyInsight(
                    category="strength",
                    title="熟练区核心工具",
                    description=f"Top: {', '.join(prof_tools[:5])}",
                    evidence=[f"共{len(prof_tools)}个熟练工具"],
                    recommendation="这些工具可跳过检索直接执行"
                ))
        except Exception:
            pass
        # v1.5: 双路径推荐洞察
        try:
            rec = get_recommender()
            rec.build(self.store_path)
            sample_queries = ["读取CSV", "搜索文件", "生成数据", "提取信息", "格式转换"]
            total_explore = sum(1 for q in sample_queries if rec.recommend(q).recommended == "exploration")
            total_ref = len(sample_queries) - total_explore
            insights.append(StrategyInsight(
                category="dual_path",
                title=f"双路径平衡: 参考{total_ref}条 探索{total_explore}条 (ε={rec.epsilon})",
                description=f"{len(sample_queries)}个样本查询中 {total_ref}个走参考路径, {total_explore}个走探索路径",
                evidence=["参考路径: 已验证经验", "探索路径: 新经验+捷径", f"ε-greedy策略(ε={rec.epsilon})"],
                recommendation="探索比例适中" if 0.1 <= total_explore/len(sample_queries) <= 0.4 else "需调整探索率"
            ))
        except Exception:
            pass

        # v1.6: 元认知门控洞察
        try:
            gate = get_gate()
            sample_tasks = [
                ("读取CSV文件并统计行数", "normal"),
                ("训练一个随机森林分类模型", "normal"),
                ("从网页提取标题", "low"),
            ]
            for task, risk in sample_tasks:
                d = gate.assess(task, risk_level=risk)
            gs = gate.get_stats()
            insights.append(StrategyInsight(
                category="metacognition",
                title=f"元认知门控: 拒答率{gs['refusal_rate']:.0%} ({gs['allowed']}允许/{gs['refused']}拒绝)",
                description=f"基于{sample_tasks[0][0]}等{sample_tasks}样本的门控决策分布",
                evidence=[f"总评估: {gs['total_assessments']}", f"允许: {gs['allowed']}", f"拒绝: {gs['refused']}"],
                recommendation=f"门控健康度{'良好' if gs['refusal_rate'] < 0.5 else '需校准'}"
            ))
        except Exception:
            pass

        # v1.7: 熵预算与耗散洞察
        try:
            budget = get_budget()
            report = budget.compute_entropy()
            actions = budget.compute_dissipation()
            archive_count = sum(1 for a in actions if a.action == "archive")
            expand_count = sum(1 for a in actions if a.action == "expand")
            recalibrate_count = sum(1 for a in actions if a.action == "recalibrate")
            
            insights.append(StrategyInsight(
                category="entropy",
                title=f"熵预算: {report.entropy_score:.2f} (多样性{report.diversity_score:.0%} 冗余{report.redundancy_score:.0%})",
                description=f"{report.total_experiences}条经验, 覆盖度{report.coverage_score:.0%}, 衰退{report.decay_count}条",
                evidence=[f"熵值: {report.entropy_score:.3f}", f"衰退: {report.decay_count}"],
                recommendation=f"熵值{'偏高，经验库健康' if report.entropy_score > 0.5 else '偏低，需增加多样性'}"
            ))
            
            if actions:
                insights.append(StrategyInsight(
                    category="dissipation",
                    title=f"耗散调度: {expand_count}扩张 {recalibrate_count}校准 {archive_count}归档",
                    description=f"基于门控审计日志的{len(actions)}条耗散动作",
                    evidence=[f"扩张: {expand_count}", f"校准: {recalibrate_count}", f"归档: {archive_count}"],
                    recommendation=f"优先处理{expand_count}个扩张项"
                ))
        except Exception:
            pass

        # v3.1: 探索路径收益分析
        try:
            from market_scheduler import get_scheduler
            sched = get_scheduler()
            md = sched.get_meltdown_stats()
            exp_rate = md.get("explore_success_rate", 0)
            expl_rate = md.get("exploit_success_rate", 0)
            exp_cnt = md.get("explore_total", 0)
            expl_cnt = md.get("exploit_total", 0)
            note = ""
            if exp_cnt > 0 and expl_cnt > 0:
                if exp_rate > expl_rate:
                    note = "探索路径收益更高 → 可增大ε"
                elif exp_rate < expl_rate:
                    note = "利用路径收益更高 → ε保持或减小"
            insights.append(StrategyInsight(
                category="exploration",
                title=f"探索路径收益: 探索{exp_cnt}次({exp_rate}) vs 利用{expl_cnt}次({expl_rate})",
                description=note or "数据不足以判断",
                evidence=[f"探索成功={md.get('explore_success',0)}", f"利用成功={md.get('exploit_success',0)}"],
                recommendation=note or "继续积累探索数据"
            ))
        except Exception:
            pass

        # v3.0: 市场调度洞察
        try:
            md = sched.get_meltdown_stats() if "sched" in dir() else {}
            melted = md.get("melted_agents", [])
            insights.append(StrategyInsight(
                category="market",
                title=f"市场调度: {len(melted)} 熔断 Agent, ε={md.get('epsilon','?')}",
                description=f"探索={md.get('explore_count',0)} 利用={md.get('exploit_count',0)}",
                evidence=[f"melted={melted}", f"ε={md.get('epsilon','?')}"],
                recommendation="检查探索/利用平衡"
            ))
        except Exception:
            pass

        # v2.5: Agent 注册表洞察
        try:
            reg = get_registry()
            reg_stats = reg.get_stats()
            insights.append(StrategyInsight(
                category="agent_registry",
                title=f"Agent 注册表: {reg_stats['total_roles']} 角色",
                description=f"已注册: {reg_stats['roles']}",
                evidence=reg_stats['roles'],
                recommendation="补充更多角色定义"
            ))
        except Exception:
            pass
        # v2.5: 仲裁器洞察
        # v2.5: 仲裁器洞察
        try:
            arb = get_arbiter()
            arb_stats = arb.get_stats()
            insights.append(StrategyInsight(
                category="arbitration",
                title=f"多 Agent 仲裁: threshold={arb_stats['threshold']}",
                description=f"Trace接入: {arb_stats['audit_connected']}",
                evidence=["加权投票: 置信度×可信度"],
                recommendation="冲突时自动仲裁"
            ))
        except Exception:
            pass
        # v3.0: 市场调度洞察
        try:
            sched = get_scheduler()
            md = sched.get_meltdown_stats()
            melted = md.get("melted_agents", [])
            insights.append(StrategyInsight(
                category="market",
                title=f"市场调度: {len(melted)} 熔断 Agent",
                description=f"熔断阈值={md['threshold']}, 熔断={melted}",
                evidence=[f"strikes={md['all_strikes']}"],
                recommendation="检查熔断Agent的失败原因"
            ))
        except Exception:
            pass
            tiers = budget._compute_experience_tier() if hasattr(budget, '_compute_experience_tier') else {}
            if tiers:
                validated = sum(1 for t in tiers.values() if t.get('tier') == 'validated')
                archived = sum(1 for t in tiers.values() if t.get('tier') == 'archived')
                insights.append(StrategyInsight(
                    category="tier_change",
                    title=f"经验晋升降级: {validated}晋升 {archived}降级",
                    description=f"{validated}条晋升, {archived}条降级",
                    evidence=[f"晋升: {validated}", f"降级: {archived}"],
                    recommendation="优先验证晋升经验的稳定性" if validated > 0 else "继续监控"
                ))

        return StrategyReport(
            summary=f"分析完成: {len(exps)} 条经验, {len(tools)} 个工具, 成功率 {success}/{len(exps)} ({success*100//max(len(exps),1)}%)",
            total_experiences=len(exps),
            insights=insights,
            tool_count=len(tools),
            success_rate=success / max(len(exps), 1),
        )

    def generate_report_text(self) -> str:
        """生成可读的策略报告"""
        report = self.analyze()
        lines = [
            f"## 策略分析报告",
            f"总览: {report.tool_count} 个工具, {report.total_experiences} 条经验, 成功率 {report.success_rate:.0%}",
            "",
        ]
        for insight in report.insights:
            lines.append(f"### [{insight.category}] {insight.title}")
            lines.append(f"  {insight.description}")
            lines.append(f"  建议: {insight.recommendation}")
            lines.append("")
        return "\n".join(lines)
