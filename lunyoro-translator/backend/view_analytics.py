"""
view_analytics.py
=================
View detailed feedback analytics and model performance comparison.

Usage:
    python view_analytics.py
    python view_analytics.py --json  # Output as JSON
"""
import sys
import json
from feedback_store import get_stats, get_detailed_analytics, get_model_comparison


def print_analytics():
    """Print formatted analytics to console."""
    print("\n" + "="*70)
    print("FEEDBACK ANALYTICS DASHBOARD")
    print("="*70 + "\n")
    
    # Basic stats
    stats = get_stats()
    print("📊 BASIC STATISTICS")
    print("-" * 70)
    print(f"Total Feedback:     {stats['total']:,}")
    print(f"Thumbs Up:          {stats['thumbs_up']:,} ({100*stats['thumbs_up']/max(stats['total'],1):.1f}%)")
    print(f"Thumbs Down:        {stats['thumbs_down']:,} ({100*stats['thumbs_down']/max(stats['total'],1):.1f}%)")
    print(f"Neutral:            {stats['neutral']:,}")
    print(f"Exportable Pairs:   {stats['exportable']:,}")
    print()
    
    # Detailed analytics
    analytics = get_detailed_analytics()
    
    print("🤖 MODEL USAGE")
    print("-" * 70)
    if analytics['model_usage']:
        for model, count in sorted(analytics['model_usage'].items(), key=lambda x: -x[1]):
            percentage = 100 * count / analytics['total_feedback']
            print(f"{model:15} {count:5,} uses ({percentage:5.1f}%)")
    else:
        print("No model usage data yet")
    print()
    
    print("⭐ MODEL RATINGS")
    print("-" * 70)
    if analytics['model_ratings']:
        for model, ratings in analytics['model_ratings'].items():
            print(f"\n{model.upper()}:")
            print(f"  Total:         {ratings['total']:,}")
            print(f"  Positive:      {ratings['positive']:,}")
            print(f"  Negative:      {ratings['negative']:,}")
            print(f"  Approval Rate: {ratings['approval_rate']:.1f}%")
    else:
        print("No rating data yet")
    print()
    
    print("🔍 MODEL COMPARISON")
    print("-" * 70)
    comparison = get_model_comparison()
    
    print("\nMarianMT:")
    marian = comparison['marian']
    print(f"  Uses:          {marian['total_uses']:,}")
    print(f"  Approval Rate: {marian['approval_rate']:.1f}%")
    print(f"  Avg Rating:    {marian['avg_rating']:.2f}")
    
    print("\nNLLB-200:")
    nllb = comparison['nllb']
    print(f"  Uses:          {nllb['total_uses']:,}")
    print(f"  Approval Rate: {nllb['approval_rate']:.1f}%")
    print(f"  Avg Rating:    {nllb['avg_rating']:.2f}")
    
    print(f"\n🏆 Winner: {comparison['winner'].upper()}")
    print(f"   Approval Rate Difference: {comparison['comparison']['approval_rate_diff']:+.1f}%")
    print()
    
    print("❌ TOP ERROR TYPES")
    print("-" * 70)
    if analytics['error_types']:
        for error, count in list(analytics['error_types'].items())[:5]:
            percentage = 100 * count / analytics['total_feedback']
            print(f"{error:25} {count:4,} ({percentage:5.1f}%)")
    else:
        print("No error data yet")
    print()
    
    print("🌍 DIRECTION STATISTICS")
    print("-" * 70)
    if analytics['direction_stats']:
        for direction, stats_dir in analytics['direction_stats'].items():
            print(f"\n{direction}:")
            print(f"  Total:         {stats_dir['total']:,}")
            print(f"  Positive:      {stats_dir['positive']:,}")
            print(f"  Approval Rate: {stats_dir['approval_rate']:.1f}%")
    else:
        print("No direction data yet")
    print()
    
    print("📝 OTHER METRICS")
    print("-" * 70)
    print(f"Correction Rate:    {analytics['correction_rate']:.1f}%")
    print(f"Unique Users:       {analytics['unique_users']:,}")
    print()
    
    print("📅 RECENT ACTIVITY (Last 10)")
    print("-" * 70)
    if analytics['recent_feedback']:
        for i, fb in enumerate(analytics['recent_feedback'][:10], 1):
            rating_emoji = "👍" if fb['rating'] > 0 else "👎" if fb['rating'] < 0 else "➖"
            model = fb['model_used'] or "unknown"
            print(f"{i:2}. {rating_emoji} {fb['direction']:8} {model:10} {fb['timestamp'][:19]}")
    else:
        print("No recent feedback")
    print()
    
    print("="*70 + "\n")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        # Output as JSON
        data = {
            "basic_stats": get_stats(),
            "detailed_analytics": get_detailed_analytics(),
            "model_comparison": get_model_comparison(),
        }
        print(json.dumps(data, indent=2))
    else:
        # Pretty print to console
        print_analytics()


if __name__ == "__main__":
    main()
