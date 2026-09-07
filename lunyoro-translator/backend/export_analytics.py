"""
export_analytics.py
===================
Export feedback data and analytics to Excel/CSV files for easy analysis.

Creates comprehensive reports with multiple sheets:
- Raw Feedback Data
- Summary Statistics
- Model Performance Comparison
- Error Analysis
- Daily Activity
- User Engagement

Usage:
    python export_analytics.py                    # Export to Excel
    python export_analytics.py --csv              # Export to CSV files
    python export_analytics.py --output report.xlsx
"""
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
from feedback_store import (
    load_all_feedback, 
    get_stats, 
    get_detailed_analytics, 
    get_model_comparison
)

BASE = Path(__file__).parent
DEFAULT_OUTPUT_DIR = BASE / "analytics_reports"


def export_raw_feedback(entries: list[dict]) -> pd.DataFrame:
    """Export raw feedback data with all fields."""
    if not entries:
        return pd.DataFrame()
    
    df = pd.DataFrame(entries)
    
    # Reorder columns for better readability
    column_order = [
        'timestamp', 'direction', 'rating', 'model_used',
        'source_text', 'translation', 'correction',
        'error_type', 'ip'
    ]
    
    # Only include columns that exist
    column_order = [col for col in column_order if col in df.columns]
    df = df[column_order]
    
    # Add human-readable columns
    df['rating_label'] = df['rating'].map({1: 'Positive', -1: 'Negative', 0: 'Neutral'})
    df['has_correction'] = df['correction'].apply(lambda x: 'Yes' if str(x).strip() else 'No')
    df['text_length'] = df['source_text'].apply(lambda x: len(str(x)))
    
    # Parse timestamp
    df['date'] = pd.to_datetime(df['timestamp'], errors='coerce').dt.date
    df['time'] = pd.to_datetime(df['timestamp'], errors='coerce').dt.time
    
    return df


def create_summary_stats() -> pd.DataFrame:
    """Create summary statistics table."""
    stats = get_stats()
    analytics = get_detailed_analytics()
    
    data = {
        'Metric': [
            'Total Feedback Submissions',
            'Positive Feedback (Thumbs Up)',
            'Negative Feedback (Thumbs Down)',
            'Neutral Feedback',
            'Approval Rate (%)',
            'Correction Rate (%)',
            'Unique Users',
            'Exportable Training Pairs',
        ],
        'Value': [
            stats['total'],
            stats['thumbs_up'],
            stats['thumbs_down'],
            stats['neutral'],
            round(100 * stats['thumbs_up'] / max(stats['total'], 1), 1),
            analytics['correction_rate'],
            analytics['unique_users'],
            stats['exportable'],
        ],
        'Description': [
            'Total number of feedback submissions received',
            'Number of positive ratings from users',
            'Number of negative ratings from users',
            'Number of neutral ratings',
            'Percentage of positive feedback',
            'Percentage of feedback with user corrections',
            'Number of unique IP addresses',
            'Number of approved pairs ready for model training',
        ]
    }
    
    return pd.DataFrame(data)


def create_model_performance() -> pd.DataFrame:
    """Create model performance comparison table."""
    comparison = get_model_comparison()
    analytics = get_detailed_analytics()
    
    rows = []
    
    # MarianMT
    marian = comparison['marian']
    rows.append({
        'Model': 'MarianMT',
        'Total Uses': marian['total_uses'],
        'Positive Feedback': marian['positive_feedback'],
        'Negative Feedback': marian['negative_feedback'],
        'Approval Rate (%)': marian['approval_rate'],
        'Average Rating': marian['avg_rating'],
        'Usage Share (%)': round(100 * marian['total_uses'] / max(analytics['total_feedback'], 1), 1),
    })
    
    # NLLB-200
    nllb = comparison['nllb']
    rows.append({
        'Model': 'NLLB-200',
        'Total Uses': nllb['total_uses'],
        'Positive Feedback': nllb['positive_feedback'],
        'Negative Feedback': nllb['negative_feedback'],
        'Approval Rate (%)': nllb['approval_rate'],
        'Average Rating': nllb['avg_rating'],
        'Usage Share (%)': round(100 * nllb['total_uses'] / max(analytics['total_feedback'], 1), 1),
    })
    
    # Both models correct
    both_data = analytics['model_ratings'].get('both', {})
    if both_data:
        rows.append({
            'Model': 'Both Correct',
            'Total Uses': both_data['total'],
            'Positive Feedback': both_data['positive'],
            'Negative Feedback': both_data['negative'],
            'Approval Rate (%)': both_data['approval_rate'],
            'Average Rating': '-',
            'Usage Share (%)': round(100 * both_data['total'] / max(analytics['total_feedback'], 1), 1),
        })
    
    # Both models wrong
    none_data = analytics['model_ratings'].get('none', {})
    if none_data:
        rows.append({
            'Model': 'Both Wrong',
            'Total Uses': none_data['total'],
            'Positive Feedback': none_data['positive'],
            'Negative Feedback': none_data['negative'],
            'Approval Rate (%)': none_data['approval_rate'],
            'Average Rating': '-',
            'Usage Share (%)': round(100 * none_data['total'] / max(analytics['total_feedback'], 1), 1),
        })
    
    df = pd.DataFrame(rows)
    
    # Add winner row
    winner_row = pd.DataFrame([{
        'Model': f'🏆 WINNER: {comparison["winner"].upper()}',
        'Total Uses': '',
        'Positive Feedback': '',
        'Negative Feedback': '',
        'Approval Rate (%)': f'Difference: {comparison["comparison"]["approval_rate_diff"]:+.1f}%',
        'Average Rating': '',
        'Usage Share (%)': '',
    }])
    
    df = pd.concat([df, winner_row], ignore_index=True)
    
    return df


def create_error_analysis() -> pd.DataFrame:
    """Create error type analysis table."""
    analytics = get_detailed_analytics()
    
    if not analytics['error_types']:
        return pd.DataFrame({'Message': ['No error data available yet']})
    
    rows = []
    total_errors = sum(analytics['error_types'].values())
    
    for error_type, count in sorted(analytics['error_types'].items(), key=lambda x: -x[1]):
        rows.append({
            'Error Type': error_type,
            'Count': count,
            'Percentage (%)': round(100 * count / total_errors, 1),
            'Description': get_error_description(error_type),
        })
    
    return pd.DataFrame(rows)


def get_error_description(error_type: str) -> str:
    """Get human-readable description for error types."""
    descriptions = {
        'grammar': 'Grammatical errors in translation',
        'spelling': 'Spelling mistakes',
        'context': 'Lack of context awareness',
        'vocabulary': 'Word not in vocabulary or wrong word choice',
        'different meaning': 'Translation has different meaning from source',
        'other': 'Other unspecified errors',
        'both_models_wrong': 'Both models produced incorrect translations',
        'both_models_correct': 'Both models produced correct translations',
    }
    return descriptions.get(error_type.lower(), 'User-reported issue')


def create_direction_stats() -> pd.DataFrame:
    """Create translation direction statistics."""
    analytics = get_detailed_analytics()
    
    if not analytics['direction_stats']:
        return pd.DataFrame({'Message': ['No direction data available yet']})
    
    rows = []
    for direction, stats in analytics['direction_stats'].items():
        direction_label = 'English → Runyoro' if direction == 'en→lun' else 'Runyoro → English'
        rows.append({
            'Direction': direction_label,
            'Direction Code': direction,
            'Total Translations': stats['total'],
            'Positive Feedback': stats['positive'],
            'Approval Rate (%)': stats['approval_rate'],
            'Usage Share (%)': round(100 * stats['total'] / analytics['total_feedback'], 1),
        })
    
    return pd.DataFrame(rows)


def create_daily_activity() -> pd.DataFrame:
    """Create daily activity timeline."""
    analytics = get_detailed_analytics()
    
    if not analytics['feedback_by_day']:
        return pd.DataFrame({'Message': ['No daily activity data available yet']})
    
    rows = []
    for date, count in sorted(analytics['feedback_by_day'].items()):
        rows.append({
            'Date': date,
            'Feedback Count': count,
            'Day of Week': pd.to_datetime(date).strftime('%A'),
        })
    
    df = pd.DataFrame(rows)
    
    # Add summary statistics
    if not df.empty:
        summary = pd.DataFrame([
            {'Date': 'AVERAGE', 'Feedback Count': df['Feedback Count'].mean(), 'Day of Week': ''},
            {'Date': 'TOTAL', 'Feedback Count': df['Feedback Count'].sum(), 'Day of Week': ''},
            {'Date': 'MAX', 'Feedback Count': df['Feedback Count'].max(), 'Day of Week': ''},
            {'Date': 'MIN', 'Feedback Count': df['Feedback Count'].min(), 'Day of Week': ''},
        ])
        df = pd.concat([df, summary], ignore_index=True)
    
    return df


def create_user_engagement() -> pd.DataFrame:
    """Create user engagement metrics."""
    entries = load_all_feedback()
    
    if not entries:
        return pd.DataFrame({'Message': ['No user data available yet']})
    
    # Group by IP address
    from collections import defaultdict
    user_stats = defaultdict(lambda: {'count': 0, 'positive': 0, 'negative': 0, 'corrections': 0})
    
    for entry in entries:
        ip = entry.get('ip', 'unknown')
        user_stats[ip]['count'] += 1
        rating = entry.get('rating', 0)
        if rating > 0:
            user_stats[ip]['positive'] += 1
        elif rating < 0:
            user_stats[ip]['negative'] += 1
        if entry.get('correction', '').strip():
            user_stats[ip]['corrections'] += 1
    
    rows = []
    for i, (ip, stats) in enumerate(sorted(user_stats.items(), key=lambda x: -x[1]['count']), 1):
        # Anonymize IP for privacy
        ip_display = f"User_{i}" if ip != 'unknown' else 'Unknown'
        rows.append({
            'User ID': ip_display,
            'Total Feedback': stats['count'],
            'Positive': stats['positive'],
            'Negative': stats['negative'],
            'Corrections Provided': stats['corrections'],
            'Engagement Score': stats['count'] + (stats['corrections'] * 2),  # Weight corrections higher
        })
    
    df = pd.DataFrame(rows)
    
    # Add summary
    if not df.empty:
        summary = pd.DataFrame([{
            'User ID': 'TOTAL USERS',
            'Total Feedback': len(entries),
            'Positive': df['Positive'].sum(),
            'Negative': df['Negative'].sum(),
            'Corrections Provided': df['Corrections Provided'].sum(),
            'Engagement Score': df['Engagement Score'].sum(),
        }])
        df = pd.concat([df, summary], ignore_index=True)
    
    return df


def export_to_excel(output_path: Path):
    """Export all analytics to a single Excel file with multiple sheets."""
    print(f"Generating analytics report...")
    
    entries = load_all_feedback()
    
    # Create Excel writer
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sheet 1: Summary Statistics
        print("  - Creating Summary Statistics sheet...")
        summary_df = create_summary_stats()
        summary_df.to_excel(writer, sheet_name='Summary Statistics', index=False)
        
        # Sheet 2: Model Performance
        print("  - Creating Model Performance sheet...")
        model_df = create_model_performance()
        model_df.to_excel(writer, sheet_name='Model Performance', index=False)
        
        # Sheet 3: Error Analysis
        print("  - Creating Error Analysis sheet...")
        error_df = create_error_analysis()
        error_df.to_excel(writer, sheet_name='Error Analysis', index=False)
        
        # Sheet 4: Direction Statistics
        print("  - Creating Direction Statistics sheet...")
        direction_df = create_direction_stats()
        direction_df.to_excel(writer, sheet_name='Direction Stats', index=False)
        
        # Sheet 5: Daily Activity
        print("  - Creating Daily Activity sheet...")
        daily_df = create_daily_activity()
        daily_df.to_excel(writer, sheet_name='Daily Activity', index=False)
        
        # Sheet 6: User Engagement
        print("  - Creating User Engagement sheet...")
        user_df = create_user_engagement()
        user_df.to_excel(writer, sheet_name='User Engagement', index=False)
        
        # Sheet 7: Raw Feedback Data
        print("  - Creating Raw Feedback Data sheet...")
        raw_df = export_raw_feedback(entries)
        if not raw_df.empty:
            raw_df.to_excel(writer, sheet_name='Raw Feedback Data', index=False)
    
    print(f"\n✅ Excel report saved to: {output_path}")
    print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")


def export_to_csv(output_dir: Path):
    """Export all analytics to separate CSV files."""
    print(f"Generating CSV reports in: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    entries = load_all_feedback()
    
    # Export each sheet as separate CSV
    files = []
    
    print("  - Exporting summary_statistics.csv...")
    summary_df = create_summary_stats()
    summary_path = output_dir / "summary_statistics.csv"
    summary_df.to_csv(summary_path, index=False)
    files.append(summary_path)
    
    print("  - Exporting model_performance.csv...")
    model_df = create_model_performance()
    model_path = output_dir / "model_performance.csv"
    model_df.to_csv(model_path, index=False)
    files.append(model_path)
    
    print("  - Exporting error_analysis.csv...")
    error_df = create_error_analysis()
    error_path = output_dir / "error_analysis.csv"
    error_df.to_csv(error_path, index=False)
    files.append(error_path)
    
    print("  - Exporting direction_statistics.csv...")
    direction_df = create_direction_stats()
    direction_path = output_dir / "direction_statistics.csv"
    direction_df.to_csv(direction_path, index=False)
    files.append(direction_path)
    
    print("  - Exporting daily_activity.csv...")
    daily_df = create_daily_activity()
    daily_path = output_dir / "daily_activity.csv"
    daily_df.to_csv(daily_path, index=False)
    files.append(daily_path)
    
    print("  - Exporting user_engagement.csv...")
    user_df = create_user_engagement()
    user_path = output_dir / "user_engagement.csv"
    user_df.to_csv(user_path, index=False)
    files.append(user_path)
    
    print("  - Exporting raw_feedback_data.csv...")
    raw_df = export_raw_feedback(entries)
    if not raw_df.empty:
        raw_path = output_dir / "raw_feedback_data.csv"
        raw_df.to_csv(raw_path, index=False)
        files.append(raw_path)
    
    print(f"\n✅ {len(files)} CSV files saved to: {output_dir}")
    for f in files:
        print(f"   - {f.name} ({f.stat().st_size / 1024:.1f} KB)")


def main():
    parser = argparse.ArgumentParser(description="Export feedback analytics to Excel/CSV")
    parser.add_argument("--csv", action="store_true",
                        help="Export to CSV files instead of Excel")
    parser.add_argument("--output", type=str,
                        help="Output file path (for Excel) or directory (for CSV)")
    
    args = parser.parse_args()
    
    # Check if we have any feedback
    entries = load_all_feedback()
    if not entries:
        print("⚠️  No feedback data found. Nothing to export.")
        return
    
    print(f"\n📊 Found {len(entries)} feedback entries to analyze\n")
    
    if args.csv:
        # Export to CSV
        if args.output:
            output_dir = Path(args.output)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = DEFAULT_OUTPUT_DIR / f"csv_export_{timestamp}"
        
        export_to_csv(output_dir)
    else:
        # Export to Excel
        if args.output:
            output_path = Path(args.output)
        else:
            DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = DEFAULT_OUTPUT_DIR / f"feedback_analytics_{timestamp}.xlsx"
        
        export_to_excel(output_path)
    
    print("\n✨ Export complete!\n")


if __name__ == "__main__":
    main()
