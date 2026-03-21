import os
import django

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bekosirs_backend.settings')
    django.setup()
    
    from products.models import ServiceRequest, ServiceQueue
    
    reqs = ServiceRequest.objects.filter(queue_entry__isnull=True).exclude(status__in=['completed', 'cancelled']).order_by('created_at')
    
    last_queue = ServiceQueue.objects.order_by('-queue_number').first()
    base_number = last_queue.queue_number if last_queue else 0
    count = 0
    
    for i, req in enumerate(reqs, start=1):
        queue_number = base_number + i
        ServiceQueue.objects.create(
            service_request=req,
            queue_number=queue_number,
            estimated_wait_time=queue_number * 30
        )
        count += 1
        print(f'Fixed SR-{req.id} with Queue {queue_number}')
    
    print(f'Total fixed: {count}')

if __name__ == '__main__':
    main()
