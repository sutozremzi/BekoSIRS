# products/views/analytics_views.py
"""
Analytics API views for dashboard and reports.

Endpoints:
- /api/analytics/sales-forecast/ - Sales predictions
- /api/analytics/customer-analytics/ - CLV and segmentation
- /api/analytics/route-optimize/ - Delivery route optimization
- /api/analytics/marketing/ - Marketing campaign stats
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from products.sales_forecast_service import SalesForecastService, get_sales_forecast_summary
from products.customer_analytics_service import CustomerAnalyticsService, get_customer_analytics_summary
from products.route_optimizer import RouteOptimizer, optimize_deliveries_for_date
from products.marketing_automation import MarketingAutomationService


class SalesForecastView(APIView):
    """
    Sales Forecast API.
    
    GET /api/analytics/sales-forecast/
        - Returns dashboard summary with top forecasts
        
    GET /api/analytics/sales-forecast/?product_id=1
        - Returns forecast for specific product
        
    GET /api/analytics/sales-forecast/?category_id=1
        - Returns aggregated forecast for category
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        if user.role not in ['admin', 'seller']:
            return Response({'error': 'Yetkisiz'}, status=status.HTTP_403_FORBIDDEN)
        
        product_id = request.query_params.get('product_id')
        category_id = request.query_params.get('category_id')
        months = int(request.query_params.get('months', 3))
        
        service = SalesForecastService()
        
        if product_id:
            result = service.forecast_product(int(product_id), months=months)
        elif category_id:
            result = service.get_category_forecast(int(category_id), months=months)
        else:
            result = get_sales_forecast_summary()
        
        return Response(result)


class CustomerAnalyticsView(APIView):
    """
    Customer Analytics (CLV) API.
    
    GET /api/analytics/customer-analytics/
        - Returns customer analytics summary
        
    GET /api/analytics/customer-analytics/?customer_id=1
        - Returns CLV for specific customer
        
    GET /api/analytics/customer-analytics/?segment=vip
        - Returns customers in specific segment
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        if user.role not in ['admin', 'seller']:
            return Response({'error': 'Yetkisiz'}, status=status.HTTP_403_FORBIDDEN)
        
        customer_id = request.query_params.get('customer_id')
        segment = request.query_params.get('segment')
        
        service = CustomerAnalyticsService()
        
        if customer_id:
            result = service.calculate_clv(int(customer_id))
        elif segment:
            result = {
                'segment': segment,
                'customers': service.get_segment_customers(segment)
            }
        else:
            result = get_customer_analytics_summary()
        
        return Response(result)


class RouteOptimizationView(APIView):
    """
    Route Optimization API.
    
    POST /api/analytics/route-optimize/
        - Optimize route for given stops
        
    Body:
    {
        "stops": [
            {"id": 1, "name": "Customer 1", "address": "...", "latitude": 41.0, "longitude": 29.0},
            ...
        ],
        "depot": {"latitude": 40.8, "longitude": 29.3},  // optional
        "return_to_depot": true  // optional
    }
    
    GET /api/analytics/route-optimize/?date=2026-01-08
        - Optimize all deliveries for a specific date
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        if user.role not in ['admin', 'seller']:
            return Response({'error': 'Yetkisiz'}, status=status.HTTP_403_FORBIDDEN)
        
        date_str = request.query_params.get('date')
        
        if date_str:
            from datetime import datetime
            try:
                delivery_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                result = optimize_deliveries_for_date(delivery_date)
            except ValueError:
                return Response(
                    {'error': 'Geçersiz tarih formatı. YYYY-MM-DD kullanın.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response({
                'message': 'Tarih belirtilmedi. POST ile durakları gönderin veya ?date=YYYY-MM-DD kullanın.',
                'usage': {
                    'GET': '/api/analytics/route-optimize/?date=2026-01-08',
                    'POST': 'Body: {"stops": [{"id": 1, "name": "...", "latitude": 41.0, "longitude": 29.0}]}'
                }
            })
        
        return Response(result)
    
    def post(self, request):
        user = request.user
        if user.role not in ['admin', 'seller']:
            return Response({'error': 'Yetkisiz'}, status=status.HTTP_403_FORBIDDEN)
        
        stops = request.data.get('stops', [])
        depot = request.data.get('depot')
        return_to_depot = request.data.get('return_to_depot', True)
        
        if not stops:
            return Response(
                {'error': 'stops listesi gerekli'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate stops have required fields
        for i, stop in enumerate(stops):
            if 'latitude' not in stop or 'longitude' not in stop:
                return Response(
                    {'error': f'Stop {i}: latitude ve longitude gerekli'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        optimizer = RouteOptimizer(depot=depot)
        result = optimizer.optimize_route(stops, return_to_depot=return_to_depot)
        
        # Add estimated times
        if result.get('route'):
            start_time = request.data.get('start_time', '09:00')
            result['route'] = optimizer.estimate_delivery_windows(result['route'], start_time)
        
        return Response(result)


class MarketingAutomationView(APIView):
    """
    Marketing Automation API.
    
    GET /api/analytics/marketing/
        - Returns marketing campaign stats and eligible customers count
        
    POST /api/analytics/marketing/
        - Run marketing campaigns
        
    Body:
    {
        "campaign": "birthday" | "churn" | "review" | "welcome" | "all",
        "dry_run": true  // optional, default false
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        if user.role != 'admin':
            return Response({'error': 'Yetkisiz'}, status=status.HTTP_403_FORBIDDEN)
        
        # Return campaign info and stats
        service = MarketingAutomationService(dry_run=True)
        
        stats = {
            'campaigns': {
                'birthday': {
                    'name': 'Doğum Günü',
                    'description': 'Doğum günü yaklaşan müşterilere indirim kuponu',
                    'eligible': service.run_birthday_campaign().get('eligible_customers', 0)
                },
                'churn_prevention': {
                    'name': 'Kayıp Önleme',
                    'description': '90+ gün inaktif müşterilere geri kazanım emaili',
                    'eligible': service.run_churn_prevention().get('eligible_customers', 0)
                },
                'review_request': {
                    'name': 'Yorum İsteği',
                    'description': 'Satın alma sonrası yorum isteği',
                    'eligible': service.run_review_request().get('eligible_customers', 0)
                },
                'welcome': {
                    'name': 'Hoş Geldin',
                    'description': 'Yeni kayıt olan müşterilere hoş geldin emaili',
                    'eligible': service.run_welcome_campaign().get('new_customers', 0)
                }
            },
            'usage': {
                'run_campaign': 'POST /api/analytics/marketing/ {"campaign": "birthday", "dry_run": false}'
            }
        }
        
        return Response(stats)
    
    def post(self, request):
        user = request.user
        if user.role != 'admin':
            return Response({'error': 'Yetkisiz'}, status=status.HTTP_403_FORBIDDEN)
        
        campaign = request.data.get('campaign', 'all')
        dry_run = request.data.get('dry_run', False)
        
        service = MarketingAutomationService(dry_run=dry_run)
        
        campaign_map = {
            'birthday': service.run_birthday_campaign,
            'churn': service.run_churn_prevention,
            'review': service.run_review_request,
            'welcome': service.run_welcome_campaign,
            'all': service.run_all_campaigns
        }
        
        if campaign not in campaign_map:
            return Response(
                {'error': f'Geçersiz kampanya tipi: {campaign}. Geçerli: {list(campaign_map.keys())}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = campaign_map[campaign]()
        result['service_stats'] = service.results
        
        return Response(result)


class ChartsView(APIView):
    """
    Dashboard Charts API.
    
    GET /api/analytics/charts/
        - Returns all chart data for dashboard
        
    GET /api/analytics/charts/?type=sales
        - Returns specific chart type
        
    Chart types: sales, revenue, customers, services
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        if user.role not in ['admin', 'seller']:
            return Response({'error': 'Yetkisiz'}, status=status.HTTP_403_FORBIDDEN)
        
        from products.charts_service import ChartsService
        service = ChartsService()
        
        chart_type = request.query_params.get('type')
        
        if chart_type == 'sales':
            months = int(request.query_params.get('months', 12))
            result = service.get_sales_trend(months)
        elif chart_type == 'daily':
            days = int(request.query_params.get('days', 30))
            result = service.get_daily_sales(days)
        elif chart_type == 'revenue':
            result = service.get_revenue_by_category()
        elif chart_type == 'products':
            limit = int(request.query_params.get('limit', 10))
            result = service.get_top_products(limit)
        elif chart_type == 'customers':
            result = service.get_customer_segments()
        elif chart_type == 'registrations':
            months = int(request.query_params.get('months', 6))
            result = service.get_customer_registrations(months)
        elif chart_type == 'services':
            result = service.get_service_requests_by_status()
        else:
            result = service.get_dashboard_charts()
        
        return Response(result)


class AuditLogView(APIView):
    """
    Audit Log API.
    
    GET /api/analytics/audit-logs/
        - Returns recent audit logs (admin only)
        
    GET /api/analytics/audit-logs/?action=login
        - Filter by action type
        
    GET /api/analytics/audit-logs/?user_id=1
        - Filter by user
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        if user.role != 'admin':
            return Response({'error': 'Yetkisiz'}, status=status.HTTP_403_FORBIDDEN)
        
        from products.models import AuditLog
        
        queryset = AuditLog.objects.all()
        
        # Filters
        action = request.query_params.get('action')
        user_id = request.query_params.get('user_id')
        model_name = request.query_params.get('model')
        limit = int(request.query_params.get('limit', 100))
        
        if action:
            queryset = queryset.filter(action=action)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if model_name:
            queryset = queryset.filter(model_name=model_name)
        
        queryset = queryset[:limit]
        
        logs = []
        for log in queryset:
            logs.append({
                'id': log.id,
                'user': log.user.username if log.user else 'Anonymous',
                'action': log.get_action_display(),
                'model': log.model_name,
                'object_id': log.object_id,
                'object_repr': log.object_repr,
                'ip_address': log.ip_address,
                'timestamp': log.timestamp.isoformat(),
                'changes': log.changes
            })
        
        return Response({
            'count': len(logs),
            'logs': logs,
            'available_actions': [choice[0] for choice in AuditLog.ACTION_CHOICES]
        })

