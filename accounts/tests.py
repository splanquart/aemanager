# coding=utf-8
from decimal import Decimal
from django.test.testcases import TransactionTestCase
import datetime
import hashlib
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import simplejson
from django.utils.formats import localize
from project.models import Proposal, PROPOSAL_STATE_DRAFT, ROW_CATEGORY_SERVICE, \
    ROW_CATEGORY_PRODUCT, PROPOSAL_STATE_BALANCED, PROPOSAL_STATE_ACCEPTED, \
    ProposalRow, VAT_RATES_19_6
from accounts.models import INVOICE_STATE_EDITED, Invoice, InvoiceRow, \
    INVOICE_STATE_SENT, InvoiceRowAmountError, PAYMENT_TYPE_CHECK, \
    PAYMENT_TYPE_CASH, Expense, INVOICE_STATE_PAID
from contact.models import Country, Contact, CONTACT_TYPE_PERSON
from autoentrepreneur.models import UserProfile
from django.contrib.webdesign import lorem_ipsum

class ExpensePermissionTest(TestCase):
    fixtures = ['test_users']

    def setUp(self):
        self.client.login(username='test', password='test')
        self.expense1 = Expense.objects.create(date=datetime.date(2010, 1, 1),
                                               reference='ABCD',
                                               amount='100.0',
                                               payment_type=PAYMENT_TYPE_CHECK,
                                               description='First expense',
                                               owner_id=1)
        self.expense2 = Expense.objects.create(date=datetime.date(2010, 2, 1),
                                               reference='BCDE',
                                               amount='200.0',
                                               payment_type=PAYMENT_TYPE_CASH,
                                               description='Second expense',
                                               owner_id=2)

    def testExpenseList(self):
        response = self.client.get(reverse('expense_list'))
        expense_list = response.context['expenses'].object_list.all()
        self.assertEquals(set(expense_list), set([self.expense1]))

    def testExpenseAdd(self):
        """
        Nothing to test for this
        """
        pass

    def testExpenseEdit(self):
        response = self.client.post(reverse('expense_edit') + '?id=%d' % (self.expense2.id),
                                    {'date': datetime.date(2010, 4, 1),
                                     'reference': 'DEFG',
                                     'amount': '400',
                                     'payment_type': PAYMENT_TYPE_CASH,
                                     'description': 'Edit payment'})
        self.assertEquals(response.status_code, 404)

    def testExpenseDelete(self):
        response = self.client.post(reverse('expense_delete'),
                                    {'id': self.expense2.id})
        self.assertEquals(response.status_code, 404)

class InvoicePermissionTest(TestCase):
    fixtures = ['test_users', 'test_contacts', 'test_projects']

    def setUp(self):
        self.client.login(username='test', password='test')
        self.proposal1 = Proposal.objects.create(project_id=30,
                                                update_date=datetime.date.today(),
                                                state=PROPOSAL_STATE_DRAFT,
                                                begin_date=datetime.date(2010, 8, 1),
                                                end_date=datetime.date(2010, 8, 15),
                                                contract_content='Content of contract',
                                                amount=2005,
                                                owner_id=1)
        self.proposal2 = Proposal.objects.create(project_id=30,
                                                update_date=datetime.date.today(),
                                                state=PROPOSAL_STATE_DRAFT,
                                                begin_date=datetime.date(2010, 8, 1),
                                                end_date=datetime.date(2010, 8, 15),
                                                contract_content='Content of contract',
                                                amount=2005,
                                                owner_id=2)
        self.invoice1 = Invoice.objects.create(customer_id=self.proposal1.project.customer_id,
                                               invoice_id=1,
                                               state=INVOICE_STATE_PAID,
                                               amount='100',
                                               edition_date=datetime.date(2010, 8, 31),
                                               payment_date=datetime.date(2010, 9, 30),
                                               paid_date=None,
                                               payment_type=PAYMENT_TYPE_CHECK,
                                               execution_begin_date=datetime.date(2010, 8, 1),
                                               execution_end_date=datetime.date(2010, 8, 7),
                                               penalty_date=datetime.date(2010, 10, 8),
                                               penalty_rate='1.5',
                                               discount_conditions='Nothing',
                                               owner_id=1)

        self.invoice1_row = InvoiceRow.objects.create(proposal_id=self.proposal1.id,
                                          invoice_id=self.invoice1.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='10',
                                          balance_payments=False,
                                          owner_id=1)

        self.invoice2 = Invoice.objects.create(customer_id=self.proposal2.project.customer_id,
                                               invoice_id=2,
                                               state=INVOICE_STATE_EDITED,
                                               amount='200',
                                               edition_date=datetime.date(2010, 8, 31),
                                               payment_date=datetime.date(2010, 9, 30),
                                               paid_date=None,
                                               payment_type=PAYMENT_TYPE_CHECK,
                                               execution_begin_date=datetime.date(2010, 8, 1),
                                               execution_end_date=datetime.date(2010, 8, 7),
                                               penalty_date=datetime.date(2010, 10, 8),
                                               penalty_rate='1.5',
                                               discount_conditions='Nothing',
                                               owner_id=2)

        self.invoice2_row = InvoiceRow.objects.create(proposal_id=self.proposal2.id,
                                          invoice_id=self.invoice2.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='20',
                                          balance_payments=False,
                                          owner_id=2)

    def testInvoiceList(self):
        response = self.client.get(reverse('invoice_list'))
        invoice_list = response.context['invoices'].all()
        self.assertEquals(set(invoice_list), set([self.invoice1]))

    def testInvoiceListExport(self):
        """
        not testable
        """
        pass

    def testInvoiceAdd(self):
        """
        test added for bug 109
        proposals displayed are not all owned
        """
        self.proposal1.state = PROPOSAL_STATE_ACCEPTED
        self.proposal1.save()
        self.proposal2.state = PROPOSAL_STATE_ACCEPTED
        self.proposal2.save()
        self.proposal2.invoice_rows.all().delete()
        response = self.client.get(reverse('invoice_add', kwargs={'customer_id': self.proposal1.project.customer.id}))
        self.assertEquals(set(response.context['invoicerowformset'].forms[0].fields['proposal'].queryset),
                          set([self.proposal1]))

    def testInvoiceAddFromProposal(self):
        self.proposal2.state = PROPOSAL_STATE_ACCEPTED
        self.proposal2.save()
        response = self.client.get(reverse('invoice_add_from_proposal', kwargs={'customer_id': self.proposal1.project.customer.id,
                                                                                'proposal_id': self.proposal2.id}))
        self.assertEqual(response.status_code, 404)

    def testInvoiceEdit(self):
        response = self.client.get(reverse('invoice_edit', kwargs={'id': self.invoice2.id}))
        self.assertEqual(response.status_code, 404)

        response = self.client.post(reverse('invoice_edit', kwargs={'id': self.invoice2.id}),
                                    {'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_SENT,
                                     'invoice-amount': 1500,
                                     'invoice-edition_date': '2010-8-30',
                                     'invoice-payment_date': '2010-9-29',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': PAYMENT_TYPE_CASH,
                                     'invoice-execution_begin_date': '2010-8-2',
                                     'invoice-execution_end_date': '2010-8-8',
                                     'invoice-penalty_date': '2010-10-9',
                                     'invoice-penalty_rate': 2,
                                     'invoice-discount_conditions':'-50%',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 1,
                                     'invoice_rows-0-proposal': self.proposal2.id,
                                     'invoice_rows-0-ownedobject_ptr': self.invoice2_row.id,
                                     'invoice_rows-0-label': 'My product',
                                     'invoice_rows-0-balance_payments': True,
                                     'invoice_rows-0-category': ROW_CATEGORY_PRODUCT,
                                     'invoice_rows-0-quantity': 5,
                                     'invoice_rows-0-unit_price': 300 })

        self.assertEqual(response.status_code, 404)


    def testInvoiceDetail(self):
        response = self.client.get(reverse('invoice_detail', kwargs={'id': self.invoice2.id}))
        self.assertEqual(response.status_code, 404)

    def testInvoiceDelete(self):
        response = self.client.get(reverse('invoice_delete', kwargs={'id': self.invoice2.id}))
        self.assertEqual(response.status_code, 404)
        response = self.client.post(reverse('invoice_delete', kwargs={'id': self.invoice2.id}),
                                    {'delete': 'Ok'})
        self.assertEqual(response.status_code, 404)

    def testInvoiceDownload(self):
        response = self.client.get(reverse('invoice_download', kwargs={'id': self.invoice2.id}))
        self.assertEqual(response.status_code, 404)

    def testInvoiceWithoutProposal(self):
        customer = self.proposal1.project.customer
        customer.owner_id = 2
        customer.save()

        response = self.client.post(reverse('invoice_add_without_proposal'),
                                    {'contact-customer_id': customer.id,
                                     'contact-name': 'New customer',
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 3,
                                     'invoice-state': INVOICE_STATE_EDITED,
                                     'invoice-amount': 1000,
                                     'invoice-edition_date': '2010-8-31',
                                     'invoice-payment_date': '2010-9-30',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': PAYMENT_TYPE_CHECK,
                                     'invoice-execution_begin_date': '2010-8-1',
                                     'invoice-execution_end_date': '2010-8-7',
                                     'invoice-penalty_date': '2010-10-8',
                                     'invoice-penalty_rate': 1.5,
                                     'invoice-discount_conditions':'Nothing',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 0,
                                     'invoice_rows-0-ownedobject_ptr': '',
                                     'invoice_rows-0-label': 'Day of work',
                                     'invoice_rows-0-proposal': '',
                                     'invoice_rows-0-category': ROW_CATEGORY_SERVICE,
                                     'invoice_rows-0-quantity': 10,
                                     'invoice_rows-0-unit_price': 100 })

        self.assertEqual(response.status_code, 404)

    def testGetContactsAjax(self):
        response = self.client.get("%s?term=contact" % (reverse('contact_ajax_search')))
        self.assertEquals(response.content, '[{"name": "Contact 1", "address__country__id": null, "address__zipcode": "", "value": "Contact 1", "label": "Contact 1", "address__city": "", "address__street": "", "id": 10}, {"name": "Contact 2", "address__country__id": null, "address__zipcode": "", "value": "Contact 2", "label": "Contact 2", "address__city": "", "address__street": "", "id": 11}]')

        customer = self.proposal1.project.customer
        customer.owner_id = 2
        customer.save()

        response = self.client.get("%s?term=contact" % (reverse('contact_ajax_search')))
        self.assertEquals(response.content, '[{"name": "Contact 2", "address__country__id": null, "address__zipcode": "", "value": "Contact 2", "label": "Contact 2", "address__city": "", "address__street": "", "id": 11}]')

    def testGetProposalsAjax(self):
        response = self.client.get("%s?customer_id=" % (reverse('invoice_proposals')))
        self.assertEqual(response.status_code, 404)

        customer = self.proposal1.project.customer

        response = self.client.get("%s?customer_id=%d" % (reverse('invoice_proposals'), customer.id))
        self.assertEqual(response.status_code, 200)

        customer.owner_id = 2
        customer.save()

        response = self.client.get("%s?customer_id=%d" % (reverse('invoice_proposals'), customer.id))
        self.assertEqual(response.status_code, 404)

class InvoiceTest(TestCase):
    fixtures = ['test_users', 'test_contacts', 'test_projects']

    def setUp(self):
        self.client.login(username='test', password='test')
        self.proposal = Proposal.objects.create(project_id=30,
                                                reference='crt1234',
                                                update_date=datetime.date.today(),
                                                state=PROPOSAL_STATE_ACCEPTED,
                                                begin_date=datetime.date(2010, 8, 1),
                                                end_date=datetime.date(2010, 8, 15),
                                                contract_content='Content of contract',
                                                amount=2005,
                                                owner_id=1)

    def testList(self):
        profile = User.objects.get(pk=1).get_profile()
        profile.creation_date = datetime.date(2010, 1, 1)
        profile.save()
        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_PAID,
                                   amount='100',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='10',
                                          balance_payments=False,
                                          owner_id=1)

        i2 = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                    invoice_id=2,
                                    state=INVOICE_STATE_EDITED,
                                    amount='200',
                                    edition_date=datetime.date(2010, 8, 31),
                                    payment_date=datetime.date(2010, 9, 30),
                                    paid_date=None,
                                    payment_type=PAYMENT_TYPE_CHECK,
                                    execution_begin_date=datetime.date(2010, 8, 1),
                                    execution_end_date=datetime.date(2010, 8, 7),
                                    penalty_date=datetime.date(2010, 10, 8),
                                    penalty_rate='1.5',
                                    discount_conditions='Nothing',
                                    owner_id=1)

        i2_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i2.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='20',
                                          balance_payments=False,
                                          owner_id=1)

        invoices = [i, i2]

        response = self.client.get(reverse('invoice_list'))
        invoice_list = response.context['invoices'].all()
        self.assertEquals(set(invoice_list), set(invoices))

    def testGetAdd(self):
        """
        Tests getting Add invoice page
        """
        response = self.client.get(reverse('invoice_add', kwargs={'customer_id': self.proposal.project.customer_id}))
        self.assertEqual(response.status_code, 200)

    def testPostAdd(self):
        """
        Tests posting to Add invoice page
        """
        response = self.client.post(reverse('invoice_add', kwargs={'customer_id': self.proposal.project.customer.id}),
                                    {'contact-name': self.proposal.project.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_EDITED,
                                     'invoice-amount': 1000,
                                     'invoice-edition_date': '2010-8-31',
                                     'invoice-payment_date': '2010-9-30',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': PAYMENT_TYPE_CHECK,
                                     'invoice-execution_begin_date': '2010-8-1',
                                     'invoice-execution_end_date': '2010-8-7',
                                     'invoice-penalty_date': '2010-10-8',
                                     'invoice-penalty_rate': 1.5,
                                     'invoice-discount_conditions':'Nothing',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 0,
                                     'invoice_rows-0-ownedobject_ptr': '',
                                     'invoice_rows-0-label': 'Day of work',
                                     'invoice_rows-0-proposal': self.proposal.id,
                                     'invoice_rows-0-category': ROW_CATEGORY_SERVICE,
                                     'invoice_rows-0-quantity': 10,
                                     'invoice_rows-0-unit_price': 100 })

        self.assertEqual(response.status_code, 302)
        result = Invoice.objects.filter(customer__id=self.proposal.project.customer.id,
                                        invoice_id=1,
                                        state=INVOICE_STATE_EDITED,
                                        amount='1000',
                                        edition_date=datetime.date(2010, 8, 31),
                                        payment_date=datetime.date(2010, 9, 30),
                                        paid_date=None,
                                        payment_type=PAYMENT_TYPE_CHECK,
                                        execution_begin_date=datetime.date(2010, 8, 1),
                                        execution_end_date=datetime.date(2010, 8, 7),
                                        penalty_date=datetime.date(2010, 10, 8),
                                        penalty_rate='1.5',
                                        discount_conditions='Nothing',
                                        owner__id=1)
        self.assertEqual(len(result), 1)
        invoice_rows = result[0].invoice_rows.all()
        self.assertEqual(len(invoice_rows), 1)
        invoice_rows = result[0].invoice_rows.filter(label='Day of work',
                                                     proposal__id=self.proposal.id,
                                                     balance_payments=False,
                                                     category=ROW_CATEGORY_SERVICE,
                                                     quantity=10,
                                                     unit_price='100')
        self.assertEqual(len(invoice_rows), 1)

    def testGetAddFromProposal(self):
        """
        Tests getting Add invoice from proposal page
        """
        p_row = ProposalRow.objects.create(proposal_id=self.proposal.id,
                                           label='Day of work',
                                           category=ROW_CATEGORY_SERVICE,
                                           quantity=12,
                                           unit_price='100',
                                           detail="detail 1",
                                           owner_id=1)
        p_row2 = ProposalRow.objects.create(proposal_id=self.proposal.id,
                                            label='Discount',
                                            category=ROW_CATEGORY_SERVICE,
                                            quantity=3,
                                            unit_price='150',
                                            detail="detail 2",
                                            owner_id=1)

        response = self.client.get(reverse('invoice_add_from_proposal', kwargs={'customer_id': self.proposal.project.customer_id,
                                                                                'proposal_id': self.proposal.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['invoiceForm'].initial['execution_begin_date'], datetime.date(2010, 8, 1))
        self.assertEqual(response.context['invoiceForm'].initial['execution_end_date'], datetime.date(2010, 8, 15))
        expected_row1 = {'category': 1,
                         'balance_payments': True,
                         'unit_price': Decimal('150.00'),
                         'label': u'Discount',
                         'proposal': self.proposal,
                         'detail': "detail 2",
                         'quantity': Decimal('3.0')}
        expected_row2 = {'category': 1,
                         'balance_payments': True,
                         'unit_price': Decimal('100.00'),
                         'label': u'Day of work',
                         'proposal': self.proposal,
                         'detail': "detail 1",
                         'quantity': Decimal('12.0')}

        row1 = response.context['invoicerowformset'].forms[0].initial
        row2 = response.context['invoicerowformset'].forms[1].initial

        verification = (expected_row1 == row1 and expected_row2 == row2) or \
                       (expected_row1 == row2 and expected_row2 == row1)
        self.assertTrue(verification)

    def testGetEdit(self):
        """
        Tests getting Edit invoice page
        """
        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   amount='1000',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          owner_id=1)

        response = self.client.get(reverse('invoice_edit', kwargs={'id': i.id}))
        self.assertEqual(response.status_code, 200)

    def testPostEdit(self):
        """
        Tests posting to Edit invoice page
        """
        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   amount='1000',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          owner_id=1)

        response = self.client.post(reverse('invoice_edit', kwargs={'id': i.id}),
                                    {'contact-name': i.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_SENT,
                                     'invoice-amount': 1500,
                                     'invoice-edition_date': '2010-8-30',
                                     'invoice-payment_date': '2010-9-29',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': PAYMENT_TYPE_CASH,
                                     'invoice-execution_begin_date': '2010-8-2',
                                     'invoice-execution_end_date': '2010-8-8',
                                     'invoice-penalty_date': '2010-10-9',
                                     'invoice-penalty_rate': 2,
                                     'invoice-discount_conditions':'-50%',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 1,
                                     'invoice_rows-0-proposal': self.proposal.id,
                                     'invoice_rows-0-ownedobject_ptr': i_row.id,
                                     'invoice_rows-0-label': 'My product',
                                     'invoice_rows-0-balance_payments': True,
                                     'invoice_rows-0-category': ROW_CATEGORY_PRODUCT,
                                     'invoice_rows-0-quantity': 5,
                                     'invoice_rows-0-unit_price': 300 })

        self.assertEqual(response.status_code, 302)
        result = Invoice.objects.filter(id=i.id,
                                        customer__id=self.proposal.project.customer.id,
                                        invoice_id=1,
                                        state=INVOICE_STATE_SENT,
                                        amount='1500',
                                        edition_date=datetime.date(2010, 8, 30),
                                        payment_date=datetime.date(2010, 9, 29),
                                        paid_date=None,
                                        payment_type=PAYMENT_TYPE_CASH,
                                        execution_begin_date=datetime.date(2010, 8, 2),
                                        execution_end_date=datetime.date(2010, 8, 8),
                                        penalty_date=datetime.date(2010, 10, 9),
                                        penalty_rate='2',
                                        discount_conditions='-50%',
                                        owner__id=1)

        self.assertEqual(len(result), 1)
        invoice_rows = result[0].invoice_rows.all()
        self.assertEqual(len(invoice_rows), 1)
        invoice_rows = result[0].invoice_rows.filter(proposal__id=self.proposal.id,
                                                     label='My product',
                                                     balance_payments=True,
                                                     category=ROW_CATEGORY_PRODUCT,
                                                     quantity=5,
                                                     unit_price='300')
        self.assertEqual(len(invoice_rows), 1)

    def testGetDelete(self):
        """
        Tests getting Delete invoice page
        """
        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   amount='1000',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          owner_id=1)

        response = self.client.get(reverse('invoice_delete', kwargs={'id': i.id}))
        self.assertEqual(response.status_code, 200)

    def testPostDelete(self):
        """
        Tests posting to Delete invoice page
        """
        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   amount='1000',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          owner_id=1)

        response = self.client.post(reverse('invoice_delete', kwargs={'id': i.id}),
                                    {'delete': 'Ok'})
        self.assertEqual(response.status_code, 302)
        result = Invoice.objects.all()
        self.assertEqual(len(result), 0)
        result = InvoiceRow.objects.all()
        self.assertEqual(len(result), 0)

    def testGetDetail(self):
        """
        Tests getting Detail invoice page
        """
        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   amount='1000',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          owner_id=1)

        response = self.client.get(reverse('invoice_detail', kwargs={'id': i.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['invoice'], i)

    def testAmountGTEProposal(self):
        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          owner_id=1)

        i2 = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                    invoice_id=2,
                                    state=INVOICE_STATE_EDITED,
                                    edition_date=datetime.date(2010, 8, 31),
                                    payment_date=datetime.date(2010, 9, 30),
                                    paid_date=None,
                                    payment_type=PAYMENT_TYPE_CHECK,
                                    execution_begin_date=datetime.date(2010, 8, 1),
                                    execution_end_date=datetime.date(2010, 8, 7),
                                    penalty_date=datetime.date(2010, 10, 8),
                                    penalty_rate='1.5',
                                    discount_conditions='Nothing',
                                    owner_id=1)

        i2_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                           invoice_id=i2.id,
                                           label='Day of work',
                                           category=ROW_CATEGORY_SERVICE,
                                           quantity=10,
                                           unit_price='100.5',
                                           balance_payments=False,
                                           owner_id=1)

        user = User.objects.get(pk=1)
        i2_row.unit_price = Decimal('100.6')
        i2_row.save(user=user)
        self.assertRaises(InvoiceRowAmountError, i2.check_amounts)

        response = self.client.post(reverse('invoice_edit', kwargs={'id': i.id}),
                                    {'contact-name': i.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_SENT,
                                     'invoice-edition_date': '2010-8-30',
                                     'invoice-payment_date': '2010-9-29',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': PAYMENT_TYPE_CHECK,
                                     'invoice-execution_begin_date': '2010-8-2',
                                     'invoice-execution_end_date': '2010-8-8',
                                     'invoice-penalty_date': '2010-10-9',
                                     'invoice-penalty_rate': 2,
                                     'invoice-discount_conditions':'-50%',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 1,
                                     'invoice_rows-0-proposal': self.proposal.id,
                                     'invoice_rows-0-ownedobject_ptr': i_row.id,
                                     'invoice_rows-0-label': 'Day of work',
                                     'invoice_rows-0-balance_payments': True,
                                     'invoice_rows-0-category': ROW_CATEGORY_SERVICE,
                                     'invoice_rows-0-quantity': 10,
                                     'invoice_rows-0-unit_price': 100.6 })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Amounts invoiced can&#39;t be greater than proposals remaining amounts")

    def testInvoiceIdIsUnique(self):
        """
        Tests that each invoice_id is unique for a user
        """
        response = self.client.post(reverse('invoice_add', kwargs={'customer_id': self.proposal.project.customer.id}),
                                    {'contact-name': self.proposal.project.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_EDITED,
                                     'invoice-amount': 1000,
                                     'invoice-edition_date': '2010-8-31',
                                     'invoice-payment_date': '2010-9-30',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': PAYMENT_TYPE_CHECK,
                                     'invoice-execution_begin_date': '2010-8-1',
                                     'invoice-execution_end_date': '2010-8-7',
                                     'invoice-penalty_date': '2010-10-8',
                                     'invoice-penalty_rate': 1.5,
                                     'invoice-discount_conditions':'Nothing',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 0,
                                     'invoice_rows-0-ownedobject_ptr': '',
                                     'invoice_rows-0-label': 'Day of work',
                                     'invoice_rows-0-proposal': self.proposal.id,
                                     'invoice_rows-0-category': ROW_CATEGORY_SERVICE,
                                     'invoice_rows-0-quantity': 10,
                                     'invoice_rows-0-unit_price': 100 })

        self.assertEqual(response.status_code, 302)
        response = self.client.post(reverse('invoice_add', kwargs={'customer_id': self.proposal.project.customer.id}),
                                    {'contact-name': self.proposal.project.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_EDITED,
                                     'invoice-amount': 1000,
                                     'invoice-edition_date': '2010-8-31',
                                     'invoice-payment_date': '2010-9-30',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': PAYMENT_TYPE_CHECK,
                                     'invoice-execution_begin_date': '2010-8-1',
                                     'invoice-execution_end_date': '2010-8-7',
                                     'invoice-penalty_date': '2010-10-8',
                                     'invoice-penalty_rate': 1.5,
                                     'invoice-discount_conditions':'Nothing',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 0,
                                     'invoice_rows-0-ownedobject_ptr': '',
                                     'invoice_rows-0-label': 'Day of work',
                                     'invoice_rows-0-proposal': self.proposal.id,
                                     'invoice_rows-0-category': ROW_CATEGORY_SERVICE,
                                     'invoice_rows-0-quantity': 10,
                                     'invoice_rows-0-unit_price': 100 })

        self.assertEqual(response.status_code, 200)
        self.assertTrue('invoice_id' in response.context['invoiceForm'].errors)

        response = self.client.post(reverse('invoice_add', kwargs={'customer_id': self.proposal.project.customer.id}),
                                    {'contact-name': self.proposal.project.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 2,
                                     'invoice-state': INVOICE_STATE_EDITED,
                                     'invoice-amount': 1000,
                                     'invoice-edition_date': '2010-8-31',
                                     'invoice-payment_date': '2010-9-30',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': PAYMENT_TYPE_CHECK,
                                     'invoice-execution_begin_date': '2010-8-1',
                                     'invoice-execution_end_date': '2010-8-7',
                                     'invoice-penalty_date': '2010-10-8',
                                     'invoice-penalty_rate': 1.5,
                                     'invoice-discount_conditions':'Nothing',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 0,
                                     'invoice_rows-0-ownedobject_ptr': '',
                                     'invoice_rows-0-label': 'Day of work',
                                     'invoice_rows-0-proposal': self.proposal.id,
                                     'invoice_rows-0-category': ROW_CATEGORY_SERVICE,
                                     'invoice_rows-0-quantity': 10,
                                     'invoice_rows-0-unit_price': 100 })

        invoice = Invoice.objects.get(invoice_id=2)
        response = self.client.post(reverse('invoice_edit', kwargs={'id': invoice.id}),
                                    {'contact-name': self.proposal.project.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_EDITED,
                                     'invoice-amount': 1000,
                                     'invoice-edition_date': '2010-8-31',
                                     'invoice-payment_date': '2010-9-30',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': PAYMENT_TYPE_CHECK,
                                     'invoice-execution_begin_date': '2010-8-1',
                                     'invoice-execution_end_date': '2010-8-7',
                                     'invoice-penalty_date': '2010-10-8',
                                     'invoice-penalty_rate': 1.5,
                                     'invoice-discount_conditions':'Nothing',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 0,
                                     'invoice_rows-0-ownedobject_ptr': '',
                                     'invoice_rows-0-label': 'Day of work',
                                     'invoice_rows-0-proposal': self.proposal.id,
                                     'invoice_rows-0-category': ROW_CATEGORY_SERVICE,
                                     'invoice_rows-0-quantity': 10,
                                     'invoice_rows-0-unit_price': 100 })

        self.assertEqual(response.status_code, 200)
        self.assertTrue('invoice_id' in response.context['invoiceForm'].errors)

    def testDownloadPdf(self):
        """
        Tests non-regression on pdf
        """
        profile = User.objects.get(pk=1).get_profile()
        profile.iban_bban = 'FR76 1234 1234 1234 1234 1234 123'
        profile.bic = 'CCBPFRABCDE'
        profile.save()
        customer_address = self.proposal.project.customer.address
        customer_address.street = u"128 boulevard des champs élysées\nEspace ZAC du champs de mars\nBP 140"
        customer_address.zipcode = '75001'
        customer_address.city = 'Paris CEDEX 1'
        customer_address.save()

        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   amount='1000',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          owner_id=1)

        response = self.client.get(reverse('invoice_download', kwargs={'id': i.id}))
        self.assertEqual(response.status_code, 200)
        f = open('/tmp/invoice.pdf', 'w')
        f.write(response.content)
        f.close()
        content = response.content.split("\n")
        invariant_content = content[0:66] + content[67:110] + content[111:-1]
        self.assertEquals(hashlib.md5("\n".join(invariant_content)).hexdigest(),
                          "8d6ca232060a96f8ad6855bdce59dc2c")

    def testBug240(self):
        """
        & character in proposal/invoice label crashes pdf download
        """
        profile = User.objects.get(pk=1).get_profile()
        profile.iban_bban = 'FR76 1234 1234 1234 1234 1234 123'
        profile.bic = 'CCBPFRABCDE'
        profile.save()
        customer_address = self.proposal.project.customer.address
        customer_address.street = u"128 boulevard des champs élysées\nEspace ZAC du champs de mars\nBP 140"
        customer_address.zipcode = '75001'
        customer_address.city = 'Paris CEDEX 1'
        customer_address.save()

        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   amount='1000',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day & work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          detail="detail & comments",
                                          owner_id=1)

        response = self.client.get(reverse('invoice_download', kwargs={'id': i.id}))
        self.assertEqual(response.status_code, 200)
        f = open('/tmp/invoice_bug240.pdf', 'w')
        f.write(response.content)
        f.close()
        content = response.content.split("\n")
        invariant_content = content[0:76] + content[77:121] + content[122:-1]
        self.assertEquals(hashlib.md5("\n".join(invariant_content)).hexdigest(),
                          "0e993bfe0f5694eb08370106e59a360a")

    def testBug245(self):
        """
        Firstname was not displayed when customer is a person
        """
        customer = self.proposal.project.customer
        customer.name = 'Dupont'
        customer.firstname = 'Pierre'
        customer.type = CONTACT_TYPE_PERSON
        customer.save()

        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   amount='1000',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          owner_id=1)

        response = self.client.get(reverse('invoice_download', kwargs={'id': i.id}))
        self.assertEqual(response.status_code, 200)
        f = open('/tmp/invoice_bug245.pdf', 'w')
        f.write(response.content)
        f.close()
        content = response.content.split("\n")
        invariant_content = content[0:66] + content[67:110] + content[111:-1]
        self.assertEquals(hashlib.md5("\n".join(invariant_content)).hexdigest(),
                          "3b9001285e1f36df25f4e6f3a005f058")

    def testInvoiceBookDownloadPdf(self):
        """
        Tests non-regression on pdf
        """
        for i in range(1, 50):
            invoice = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=i,
                                   state=INVOICE_STATE_PAID,
                                   amount='1',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=datetime.date(2010, 9, 30),
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

            i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=invoice.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='1',
                                          balance_payments=False,
                                          owner_id=1)

        response = self.client.get(reverse('invoice_list_export') + '?year=%(year)s' % {'year': '2010'})
        self.assertEqual(response.status_code, 200)
        f = open('/tmp/invoice_book.pdf', 'w')
        f.write(response.content)
        f.close()
        content = response.content.split("\n")
        invariant_content = content[0:85] + content[86:141] + content[142:-1]
        self.assertEquals(hashlib.md5("\n".join(invariant_content)).hexdigest(),
                          "0f36d5d79e6069410a8fe86070ae0d15")

    def testBalancePayment(self):
        """
        Tests changing state of proposal to balanced
        """
        response = self.client.post(reverse('invoice_add', kwargs={'customer_id': self.proposal.project.customer.id}),
                                    {'contact-name': self.proposal.project.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_PAID,
                                     'invoice-amount': 1000,
                                     'invoice-edition_date': '2010-8-31',
                                     'invoice-payment_date': '2010-9-30',
                                     'invoice-paid_date': '2010-10-30',
                                     'invoice-payment_type': PAYMENT_TYPE_CHECK,
                                     'invoice-execution_begin_date': '2010-8-1',
                                     'invoice-execution_end_date': '2010-8-7',
                                     'invoice-penalty_date': '2010-10-8',
                                     'invoice-penalty_rate': 1.5,
                                     'invoice-discount_conditions':'Nothing',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 0,
                                     'invoice_rows-0-ownedobject_ptr': '',
                                     'invoice_rows-0-label': 'Day of work',
                                     'invoice_rows-0-proposal': self.proposal.id,
                                     'invoice_rows-0-category': ROW_CATEGORY_SERVICE,
                                     'invoice_rows-0-quantity': 10,
                                     'invoice_rows-0-unit_price': 100,
                                     'invoice_rows-0-balance_payments': True })

        self.assertEquals(response.status_code, 302)
        proposal = Proposal.objects.get(pk=self.proposal.id)
        self.assertEquals(proposal.state, PROPOSAL_STATE_BALANCED)
        self.assertEquals(proposal.get_remaining_to_invoice(), 0)

    def testPaymentTypeIsMandatoryWhenPaid(self):
        """
        Tests that payment type is not mandatory except when state is set to
        paid
        """
        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   amount='1000',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=None,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          owner_id=1)

        response = self.client.post(reverse('invoice_edit', kwargs={'id': i.id}),
                                    {'contact-name': i.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_SENT,
                                     'invoice-amount': 1500,
                                     'invoice-edition_date': '2010-8-30',
                                     'invoice-payment_date': '2010-9-29',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': '',
                                     'invoice-execution_begin_date': '2010-8-2',
                                     'invoice-execution_end_date': '2010-8-8',
                                     'invoice-penalty_date': '2010-10-9',
                                     'invoice-penalty_rate': 2,
                                     'invoice-discount_conditions':'-50%',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 1,
                                     'invoice_rows-0-proposal': self.proposal.id,
                                     'invoice_rows-0-ownedobject_ptr': i_row.id,
                                     'invoice_rows-0-label': 'My product',
                                     'invoice_rows-0-balance_payments': True,
                                     'invoice_rows-0-category': ROW_CATEGORY_PRODUCT,
                                     'invoice_rows-0-quantity': 5,
                                     'invoice_rows-0-unit_price': 300 })

        self.assertEqual(response.status_code, 302)

        response = self.client.post(reverse('invoice_edit', kwargs={'id': i.id}),
                                    {'contact-name': i.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_PAID,
                                     'invoice-amount': 1500,
                                     'invoice-edition_date': '2010-8-30',
                                     'invoice-payment_date': '2010-9-29',
                                     'invoice-paid_date': '2010-9-29',
                                     'invoice-payment_type': '',
                                     'invoice-execution_begin_date': '2010-8-2',
                                     'invoice-execution_end_date': '2010-8-8',
                                     'invoice-penalty_date': '2010-10-9',
                                     'invoice-penalty_rate': 2,
                                     'invoice-discount_conditions':'-50%',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 1,
                                     'invoice_rows-0-proposal': self.proposal.id,
                                     'invoice_rows-0-ownedobject_ptr': i_row.id,
                                     'invoice_rows-0-label': 'My product',
                                     'invoice_rows-0-balance_payments': True,
                                     'invoice_rows-0-category': ROW_CATEGORY_PRODUCT,
                                     'invoice_rows-0-quantity': 5,
                                     'invoice_rows-0-unit_price': 300 })

        self.assertEqual(response.status_code, 200)
        self.assertTrue('payment_type' in response.context['invoiceForm'].errors)

        response = self.client.post(reverse('invoice_edit', kwargs={'id': i.id}),
                                    {'contact-name': i.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_PAID,
                                     'invoice-amount': 1500,
                                     'invoice-edition_date': '2010-8-30',
                                     'invoice-payment_date': '2010-9-29',
                                     'invoice-paid_date': '2010-9-29',
                                     'invoice-payment_type': PAYMENT_TYPE_CASH,
                                     'invoice-execution_begin_date': '2010-8-2',
                                     'invoice-execution_end_date': '2010-8-8',
                                     'invoice-penalty_date': '2010-10-9',
                                     'invoice-penalty_rate': 2,
                                     'invoice-discount_conditions':'-50%',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 1,
                                     'invoice_rows-0-proposal': self.proposal.id,
                                     'invoice_rows-0-ownedobject_ptr': i_row.id,
                                     'invoice_rows-0-label': 'My product',
                                     'invoice_rows-0-balance_payments': True,
                                     'invoice_rows-0-category': ROW_CATEGORY_PRODUCT,
                                     'invoice_rows-0-quantity': 5,
                                     'invoice_rows-0-unit_price': 300 })

        self.assertEqual(response.status_code, 302)

    def testBug72(self):
        """
        Removing invoice rows do not update invoice amount
        """
        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   amount='1000',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=2,
                                          unit_price='100',
                                          balance_payments=False,
                                          owner_id=1)
        i_row2 = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                           invoice_id=i.id,
                                           label='Day of work',
                                           category=ROW_CATEGORY_SERVICE,
                                           quantity=4,
                                           unit_price='200',
                                           balance_payments=False,
                                           owner_id=1)

        response = self.client.post(reverse('invoice_edit', kwargs={'id': i.id}),
                                    {'contact-name': i.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_SENT,
                                     'invoice-amount': 1500,
                                     'invoice-edition_date': '2010-8-30',
                                     'invoice-payment_date': '2010-9-29',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': PAYMENT_TYPE_CASH,
                                     'invoice-execution_begin_date': '2010-8-2',
                                     'invoice-execution_end_date': '2010-8-8',
                                     'invoice-penalty_date': '2010-10-9',
                                     'invoice-penalty_rate': 2,
                                     'invoice-discount_conditions':'-50%',
                                     'invoice_rows-TOTAL_FORMS': 2,
                                     'invoice_rows-INITIAL_FORMS': 2,
                                     'invoice_rows-0-proposal': self.proposal.id,
                                     'invoice_rows-0-ownedobject_ptr': i_row.id,
                                     'invoice_rows-0-label': 'My product',
                                     'invoice_rows-0-balance_payments': False,
                                     'invoice_rows-0-category': ROW_CATEGORY_PRODUCT,
                                     'invoice_rows-0-quantity': 2,
                                     'invoice_rows-0-unit_price': 100,
                                     'invoice_rows-1-proposal': self.proposal.id,
                                     'invoice_rows-1-ownedobject_ptr': i_row2.id,
                                     'invoice_rows-1-label': 'My product',
                                     'invoice_rows-1-balance_payments': False,
                                     'invoice_rows-1-category': ROW_CATEGORY_PRODUCT,
                                     'invoice_rows-1-quantity': 4,
                                     'invoice_rows-1-unit_price': 200,
                                     'invoice_rows-1-DELETE': 'checked'})

        self.assertEquals(float(Invoice.objects.get(pk=i.id).amount), 200.0)

    def testBug98(self):
        """
        If state is set to paid, user must fill a paid_date
        If paid_date is set, state is set to paid
        """
        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_SENT,
                                   amount='1000',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          owner_id=1)

        response = self.client.post(reverse('invoice_edit', kwargs={'id': i.id}),
                                    {'contact-name': i.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_PAID,
                                     'invoice-amount': 1000,
                                     'invoice-edition_date': '2010-8-30',
                                     'invoice-payment_date': '2010-9-29',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': PAYMENT_TYPE_CASH,
                                     'invoice-execution_begin_date': '2010-8-2',
                                     'invoice-execution_end_date': '2010-8-8',
                                     'invoice-penalty_date': '2010-10-9',
                                     'invoice-penalty_rate': 2,
                                     'invoice-discount_conditions':'-50%',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 1,
                                     'invoice_rows-0-proposal': self.proposal.id,
                                     'invoice_rows-0-ownedobject_ptr': i_row.id,
                                     'invoice_rows-0-label': 'My product',
                                     'invoice_rows-0-balance_payments': False,
                                     'invoice_rows-0-category': ROW_CATEGORY_PRODUCT,
                                     'invoice_rows-0-quantity': 10,
                                     'invoice_rows-0-unit_price': 100
                                     })

        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(response.context['invoiceForm'].errors), 1)

        i.state = INVOICE_STATE_SENT
        i.save()
        response = self.client.post(reverse('invoice_edit', kwargs={'id': i.id}),
                                    {'contact-name': i.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_EDITED,
                                     'invoice-amount': 1000,
                                     'invoice-edition_date': '2010-8-30',
                                     'invoice-payment_date': '2010-9-29',
                                     'invoice-paid_date': '2010-9-29',
                                     'invoice-payment_type': PAYMENT_TYPE_CASH,
                                     'invoice-execution_begin_date': '2010-8-2',
                                     'invoice-execution_end_date': '2010-8-8',
                                     'invoice-penalty_date': '2010-10-9',
                                     'invoice-penalty_rate': 2,
                                     'invoice-discount_conditions':'-50%',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 1,
                                     'invoice_rows-0-proposal': self.proposal.id,
                                     'invoice_rows-0-ownedobject_ptr': i_row.id,
                                     'invoice_rows-0-label': 'My product',
                                     'invoice_rows-0-balance_payments': False,
                                     'invoice_rows-0-category': ROW_CATEGORY_PRODUCT,
                                     'invoice_rows-0-quantity': 10,
                                     'invoice_rows-0-unit_price': 100
                                     })
        self.assertEquals(response.status_code, 302)
        self.assertEquals(Invoice.objects.get(pk=i.id).state, INVOICE_STATE_PAID)

    def testBug96(self):
        """
        Negative value raise exception if a positive row
        is greater than proposal amount
        """
        p = Proposal.objects.create(project_id=30,
                                    update_date=datetime.date.today(),
                                    state=PROPOSAL_STATE_ACCEPTED,
                                    begin_date=datetime.date(2010, 8, 1),
                                    end_date=datetime.date(2010, 8, 15),
                                    contract_content='Content of contract',
                                    amount=1100,
                                    owner_id=1)

        p_row = ProposalRow.objects.create(proposal_id=p.id,
                                           label='Day of work',
                                           category=ROW_CATEGORY_SERVICE,
                                           quantity=12,
                                           unit_price='100',
                                           owner_id=1)
        p_row2 = ProposalRow.objects.create(proposal_id=p.id,
                                            label='Discount',
                                            category=ROW_CATEGORY_SERVICE,
                                            quantity= -1,
                                            unit_price='100',
                                            owner_id=1)

        response = self.client.post(reverse('invoice_add', kwargs={'customer_id': p.project.customer.id}),
                                    {'contact-name': p.project.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_EDITED,
                                     'invoice-edition_date': '2010-8-31',
                                     'invoice-payment_date': '2010-9-30',
                                     'invoice-paid_date': '2010-10-30',
                                     'invoice-payment_type': PAYMENT_TYPE_CHECK,
                                     'invoice-execution_begin_date': '2010-8-1',
                                     'invoice-execution_end_date': '2010-8-7',
                                     'invoice-penalty_date': '2010-10-8',
                                     'invoice-penalty_rate': 1.5,
                                     'invoice-discount_conditions':'Nothing',
                                     'invoice_rows-TOTAL_FORMS': 2,
                                     'invoice_rows-INITIAL_FORMS': 0,
                                     'invoice_rows-0-ownedobject_ptr': '',
                                     'invoice_rows-0-label': 'Day of work',
                                     'invoice_rows-0-proposal': p.id,
                                     'invoice_rows-0-category': ROW_CATEGORY_SERVICE,
                                     'invoice_rows-0-quantity': 12,
                                     'invoice_rows-0-unit_price': 100,
                                     'invoice_rows-0-balance_payments': True,
                                     'invoice_rows-1-ownedobject_ptr': '',
                                     'invoice_rows-1-label': 'Discount',
                                     'invoice_rows-1-proposal': p.id,
                                     'invoice_rows-1-category': ROW_CATEGORY_SERVICE,
                                     'invoice_rows-1-quantity':-1,
                                     'invoice_rows-1-unit_price': 100,
                                     'invoice_rows-1-balance_payments': True })

        self.assertEquals(response.status_code, 302)
        self.assertEquals(Invoice.objects.get(invoice_id=1).amount, 1100)

    def testBug141(self):
        """
        Non ascii characters make invoice download crashes
        """
        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   amount='1000',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Néant',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Test accent é',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          owner_id=1)

        response = self.client.get(reverse('invoice_download', kwargs={'id': i.id}))
        self.assertEqual(response.status_code, 200)

        self.proposal.reference = ''
        self.proposal.save()

        response = self.client.get(reverse('invoice_download', kwargs={'id': i.id}))
        self.assertEqual(response.status_code, 200)

    def testBug204(self):
        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   amount='1000',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          owner_id=1)

        response = self.client.post(reverse('invoice_edit', kwargs={'id': i.id}),
                                    {'contact-name': i.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_SENT,
                                     'invoice-amount': 1500,
                                     'invoice-edition_date': '2010-8-30',
                                     'invoice-payment_date': '2010-9-29',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': PAYMENT_TYPE_CASH,
                                     'invoice-execution_begin_date': '2010-8-2',
                                     'invoice-execution_end_date': '2010-8-8',
                                     'invoice-penalty_date': '2010-10-9',
                                     'invoice-penalty_rate': 2,
                                     'invoice-discount_conditions':'-50%',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 1,
                                     'invoice_rows-0-proposal': self.proposal.id,
                                     'invoice_rows-0-ownedobject_ptr': i_row.id,
                                     'invoice_rows-0-label': 'My product',
                                     'invoice_rows-0-balance_payments': True,
                                     'invoice_rows-0-category': ROW_CATEGORY_PRODUCT,
                                     'invoice_rows-0-quantity': '',
                                     'invoice_rows-0-unit_price': 300,
                                     'invoice_rows-0-DELETE': 'on'})

        self.assertEqual(response.status_code, 302)

    def testBug206(self):
        response = self.client.post(reverse('invoice_add', kwargs={'customer_id': self.proposal.project.customer.id}),
                                    {
                                     u'invoice_rows-0-ownedobject_ptr': [u''],
                                     u'invoice-state': [u'1'],
                                     u'invoice-penalty_date': [u''],
                                     u'invoice-execution_begin_date': [u''],
                                     u'invoice_rows-MAX_NUM_FORMS': [u''],
                                     u'invoice-payment_date': [u'2011-05-25'],
                                     u'invoice_rows-0-proposal': [u''],
                                     u'invoice-payment_type': [u'2'],
                                     u'invoice_rows-0-quantity': [u''],
                                     u'invoice-discount_conditions': [u''],
                                     u'invoice-paid_date': [u''],
                                     u'invoice-edition_date': [u'2011-04-25'],
                                     u'invoice-execution_end_date': [u''],
                                     u'invoice_rows-INITIAL_FORMS': [u'0'],
                                     u'invoice_rows-TOTAL_FORMS': [u'1'],
                                     u'invoice_rows-0-label': [u''],
                                     u'invoice_rows-0-unit_price': [u''],
                                     u'invoice_rows-0-category': [u''],
                                     u'invoice-invoice_id': [u'20110425001'],
                                     u'action': [u'Sauvegarder'],
                                     u'invoice-penalty_rate': [u'']
                                     })

        self.assertEqual(response.status_code, 200)
        self.assertTrue('invoice_id' in response.context['invoiceForm'].errors)

    def testBug207(self):
        """
        Tests that non ascii characters in user's country works
        """
        profile = User.objects.get(pk=1).get_profile()
        profile.iban_bban = 'FR76 1234 1234 1234 1234 1234 123'
        profile.bic = 'CCBPFRABCDE'
        profile.save()
        address = profile.address
        address.country = Country.objects.get(country_code2='AX')
        address.save()

        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   amount='1000',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          owner_id=1)

        response = self.client.get(reverse('invoice_download', kwargs={'id': i.id}))
        self.assertEqual(response.status_code, 200)

    def testVat(self):
        profile = UserProfile.objects.get(user=1)
        profile.vat_number = 'FR010123456789123'
        profile.save()

        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   amount='2',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=1,
                                          unit_price='1',
                                          balance_payments=False,
                                          vat_rate=VAT_RATES_19_6,
                                          owner_id=1)
        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=1,
                                          unit_price='1',
                                          balance_payments=False,
                                          vat_rate=VAT_RATES_19_6,
                                          owner_id=1)
        response = self.client.get(reverse('invoice_detail', kwargs={'id': i.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['invoice'].get_vat(), Decimal('0.392'))
        self.assertEqual(response.context['invoice'].amount_including_tax(), Decimal('2.392'))

    def testDownloadPdfWithVat(self):
        """
        Tests non-regression on pdf
        """
        profile = User.objects.get(pk=1).get_profile()
        profile.iban_bban = 'FR76 1234 1234 1234 1234 1234 123'
        profile.bic = 'CCBPFRABCDE'
        profile.vat_number = 'FR010123456789123'
        profile.save()
        customer_address = self.proposal.project.customer.address
        customer_address.street = u"128 boulevard des champs élysées\nEspace ZAC du champs de mars\nBP 140"
        customer_address.zipcode = '75001'
        customer_address.city = 'Paris CEDEX 1'
        customer_address.save()

        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   amount='1000',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          vat_rate=VAT_RATES_19_6,
                                          owner_id=1)

        response = self.client.get(reverse('invoice_download', kwargs={'id': i.id}))
        self.assertEqual(response.status_code, 200)
        f = open('/tmp/invoiceVat.pdf', 'w')
        f.write(response.content)
        f.close()
        content = response.content.split("\n")
        invariant_content = content[0:66] + content[67:110] + content[111:-1]
        self.assertEquals(hashlib.md5("\n".join(invariant_content)).hexdigest(),
                          "5cbe0bd475ed4aa5f46ce91d06f56992")

    def testDownloadPdfWithRowDetail(self):
        """
        Tests non-regression on pdf with row detail set
        """
        profile = User.objects.get(pk=1).get_profile()
        profile.iban_bban = 'FR76 1234 1234 1234 1234 1234 123'
        profile.bic = 'CCBPFRABCDE'
        profile.vat_number = 'FR010123456789123'
        profile.save()
        customer_address = self.proposal.project.customer.address
        customer_address.street = u"128 boulevard des champs élysées\nEspace ZAC du champs de mars\nBP 140"
        customer_address.zipcode = '75001'
        customer_address.city = 'Paris CEDEX 1'
        customer_address.save()

        i = Invoice.objects.create(customer_id=self.proposal.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_EDITED,
                                   amount='1000',
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          vat_rate=VAT_RATES_19_6,
                                          detail=lorem_ipsum.COMMON_P,
                                          owner_id=1)
        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          vat_rate=VAT_RATES_19_6,
                                          detail=lorem_ipsum.COMMON_P,
                                          owner_id=1)
        i_row = InvoiceRow.objects.create(proposal_id=self.proposal.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          vat_rate=VAT_RATES_19_6,
                                          detail=lorem_ipsum.COMMON_P,
                                          owner_id=1)

        response = self.client.get(reverse('invoice_download', kwargs={'id': i.id}))
        self.assertEqual(response.status_code, 200)
        f = open('/tmp/invoice_row_detail.pdf', 'w')
        f.write(response.content)
        f.close()
        content = response.content.split("\n")
        invariant_content = content[0:95] + content[96:152] + content[153:-1]
        self.assertEquals(hashlib.md5("\n".join(invariant_content)).hexdigest(),
                          "f65bdc5502bf75def1ed0fae9ff1b399")

    def testCanCreateInvoiceWithoutProposal(self):
        contacts = Contact.objects.filter(name='New customer').count()
        self.assertEquals(contacts, 0)
        response = self.client.post(reverse('invoice_add_without_proposal'),
                                    {'contact-name': 'New customer',
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_EDITED,
                                     'invoice-amount': 1000,
                                     'invoice-edition_date': '2010-8-31',
                                     'invoice-payment_date': '2010-9-30',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': PAYMENT_TYPE_CHECK,
                                     'invoice-execution_begin_date': '2010-8-1',
                                     'invoice-execution_end_date': '2010-8-7',
                                     'invoice-penalty_date': '2010-10-8',
                                     'invoice-penalty_rate': 1.5,
                                     'invoice-discount_conditions':'Nothing',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 0,
                                     'invoice_rows-0-ownedobject_ptr': '',
                                     'invoice_rows-0-label': 'Day of work',
                                     'invoice_rows-0-proposal': '',
                                     'invoice_rows-0-category': ROW_CATEGORY_SERVICE,
                                     'invoice_rows-0-quantity': 10,
                                     'invoice_rows-0-unit_price': 100 })

        self.assertEqual(response.status_code, 302)

        customer = Contact.objects.get(name='New customer')
        result = Invoice.objects.filter(customer__id=customer.id,
                                        invoice_id=1,
                                        state=INVOICE_STATE_EDITED,
                                        amount='1000',
                                        edition_date=datetime.date(2010, 8, 31),
                                        payment_date=datetime.date(2010, 9, 30),
                                        paid_date=None,
                                        payment_type=PAYMENT_TYPE_CHECK,
                                        execution_begin_date=datetime.date(2010, 8, 1),
                                        execution_end_date=datetime.date(2010, 8, 7),
                                        penalty_date=datetime.date(2010, 10, 8),
                                        penalty_rate='1.5',
                                        discount_conditions='Nothing',
                                        owner__id=1)
        self.assertEqual(len(result), 1)
        invoice_rows = result[0].invoice_rows.all()
        self.assertEqual(len(invoice_rows), 1)
        invoice_rows = result[0].invoice_rows.filter(label='Day of work',
                                                     proposal__id=None,
                                                     balance_payments=False,
                                                     category=ROW_CATEGORY_SERVICE,
                                                     quantity=10,
                                                     unit_price='100')
        self.assertEqual(len(invoice_rows), 1)

    def testBug242(self):
        contacts = Contact.objects.filter(name='New customer').count()
        self.assertEquals(contacts, 0)
        response = self.client.post(reverse('invoice_add_without_proposal'),
                                    {'contact-name': 'New customer',
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_PAID,
                                     'invoice-amount': 1000,
                                     'invoice-edition_date': '2010-8-31',
                                     'invoice-payment_date': '2010-9-30',
                                     'invoice-paid_date': '2010-10-10',
                                     'invoice-payment_type': PAYMENT_TYPE_CHECK,
                                     'invoice-execution_begin_date': '2010-8-1',
                                     'invoice-execution_end_date': '2010-8-7',
                                     'invoice-penalty_date': '2010-10-8',
                                     'invoice-penalty_rate': 1.5,
                                     'invoice-discount_conditions':'Nothing',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 0,
                                     'invoice_rows-0-ownedobject_ptr': '',
                                     'invoice_rows-0-label': 'Day of work',
                                     'invoice_rows-0-proposal': '',
                                     'invoice_rows-0-balance_payments': 'on',
                                     'invoice_rows-0-category': ROW_CATEGORY_SERVICE,
                                     'invoice_rows-0-quantity': 10,
                                     'invoice_rows-0-unit_price': 100 })

        self.assertEqual(response.status_code, 302)

    def testCanReferenceExistentContact(self):
        self.assertEquals(Contact.objects.count(), 2)

        response = self.client.post(reverse('invoice_add_without_proposal'),
                                    {'contact-customer_id': self.proposal.project.customer.id,
                                     'contact-name': 'New customer',
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_EDITED,
                                     'invoice-amount': 1000,
                                     'invoice-edition_date': '2010-8-31',
                                     'invoice-payment_date': '2010-9-30',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': PAYMENT_TYPE_CHECK,
                                     'invoice-execution_begin_date': '2010-8-1',
                                     'invoice-execution_end_date': '2010-8-7',
                                     'invoice-penalty_date': '2010-10-8',
                                     'invoice-penalty_rate': 1.5,
                                     'invoice-discount_conditions':'Nothing',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 0,
                                     'invoice_rows-0-ownedobject_ptr': '',
                                     'invoice_rows-0-label': 'Day of work',
                                     'invoice_rows-0-proposal': '',
                                     'invoice_rows-0-category': ROW_CATEGORY_SERVICE,
                                     'invoice_rows-0-quantity': 10,
                                     'invoice_rows-0-unit_price': 100 })

        self.assertEqual(response.status_code, 302)

        self.assertEquals(Contact.objects.count(), 2)

        result = Invoice.objects.filter(customer__id=self.proposal.project.customer.id,
                                        invoice_id=1,
                                        state=INVOICE_STATE_EDITED,
                                        amount='1000',
                                        edition_date=datetime.date(2010, 8, 31),
                                        payment_date=datetime.date(2010, 9, 30),
                                        paid_date=None,
                                        payment_type=PAYMENT_TYPE_CHECK,
                                        execution_begin_date=datetime.date(2010, 8, 1),
                                        execution_end_date=datetime.date(2010, 8, 7),
                                        penalty_date=datetime.date(2010, 10, 8),
                                        penalty_rate='1.5',
                                        discount_conditions='Nothing',
                                        owner__id=1)
        self.assertEqual(len(result), 1)

    def testCanModifyContactAddress(self):
        customer = self.proposal.project.customer
        self.assertEquals(customer.address.street, '')
        self.assertEquals(customer.address.zipcode, '')
        self.assertEquals(customer.address.city, '')
        self.assertEquals(customer.address.country_id, None)

        response = self.client.post(reverse('invoice_add_without_proposal'),
                                    {'contact-customer_id': self.proposal.project.customer.id,
                                     'contact-name': 'New customer',
                                     'address-street': '2 rue du calvaire',
                                     'address-zipcode': '33000',
                                     'address-city': 'Bordeaux',
                                     'address-country': 10,
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_EDITED,
                                     'invoice-amount': 1000,
                                     'invoice-edition_date': '2010-8-31',
                                     'invoice-payment_date': '2010-9-30',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': PAYMENT_TYPE_CHECK,
                                     'invoice-execution_begin_date': '2010-8-1',
                                     'invoice-execution_end_date': '2010-8-7',
                                     'invoice-penalty_date': '2010-10-8',
                                     'invoice-penalty_rate': 1.5,
                                     'invoice-discount_conditions':'Nothing',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 0,
                                     'invoice_rows-0-ownedobject_ptr': '',
                                     'invoice_rows-0-label': 'Day of work',
                                     'invoice_rows-0-proposal': '',
                                     'invoice_rows-0-category': ROW_CATEGORY_SERVICE,
                                     'invoice_rows-0-quantity': 10,
                                     'invoice_rows-0-unit_price': 100 })

        self.assertEqual(response.status_code, 302)

        invoice = Invoice.objects.get(invoice_id=1)
        customer = invoice.customer
        self.assertEquals(customer.address.street, '2 rue du calvaire')
        self.assertEquals(customer.address.zipcode, '33000')
        self.assertEquals(customer.address.city, 'Bordeaux')
        self.assertEquals(customer.address.country_id, 10)

    def testCannotModifyContactName(self):
        customer = self.proposal.project.customer
        self.assertEquals(customer.name, 'Contact 1')

        response = self.client.post(reverse('invoice_add_without_proposal'),
                                    {'contact-customer_id': self.proposal.project.customer.id,
                                     'contact-name': 'New customer',
                                     'address-street': '2 rue du calvaire',
                                     'address-zipcode': '33000',
                                     'address-city': 'Bordeaux',
                                     'address-country': 10,
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_EDITED,
                                     'invoice-amount': 1000,
                                     'invoice-edition_date': '2010-8-31',
                                     'invoice-payment_date': '2010-9-30',
                                     'invoice-paid_date': '',
                                     'invoice-payment_type': PAYMENT_TYPE_CHECK,
                                     'invoice-execution_begin_date': '2010-8-1',
                                     'invoice-execution_end_date': '2010-8-7',
                                     'invoice-penalty_date': '2010-10-8',
                                     'invoice-penalty_rate': 1.5,
                                     'invoice-discount_conditions':'Nothing',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 0,
                                     'invoice_rows-0-ownedobject_ptr': '',
                                     'invoice_rows-0-label': 'Day of work',
                                     'invoice_rows-0-proposal': '',
                                     'invoice_rows-0-category': ROW_CATEGORY_SERVICE,
                                     'invoice_rows-0-quantity': 10,
                                     'invoice_rows-0-unit_price': 100 })

        self.assertEqual(response.status_code, 302)

        invoice = Invoice.objects.get(invoice_id=1)
        customer = invoice.customer
        self.assertEquals(customer.name, 'Contact 1')

class InvoiceBug106Test(TransactionTestCase):
    fixtures = ['test_users', 'test_contacts', 'test_projects']

    def setUp(self):
        self.client.login(username='test', password='test')

    def testBug106(self):
        """
        Saving fails when editing an invoice when another is balancing
        """
        p = Proposal.objects.create(project_id=30,
                                    update_date=datetime.date.today(),
                                    state=PROPOSAL_STATE_ACCEPTED,
                                    begin_date=datetime.date(2010, 8, 1),
                                    end_date=datetime.date(2010, 8, 15),
                                    contract_content='Content of contract',
                                    amount=2000,
                                    owner_id=1)

        p_row = ProposalRow.objects.create(proposal_id=p.id,
                                           label='Day of work',
                                           category=ROW_CATEGORY_SERVICE,
                                           quantity=20,
                                           unit_price='100',
                                           owner_id=1)

        i = Invoice.objects.create(customer_id=p.project.customer_id,
                                   invoice_id=1,
                                   state=INVOICE_STATE_SENT,
                                   edition_date=datetime.date(2010, 8, 31),
                                   payment_date=datetime.date(2010, 9, 30),
                                   paid_date=None,
                                   payment_type=PAYMENT_TYPE_CHECK,
                                   execution_begin_date=datetime.date(2010, 8, 1),
                                   execution_end_date=datetime.date(2010, 8, 7),
                                   penalty_date=datetime.date(2010, 10, 8),
                                   penalty_rate='1.5',
                                   discount_conditions='Nothing',
                                   owner_id=1)

        i_row = InvoiceRow.objects.create(proposal_id=p.id,
                                          invoice_id=i.id,
                                          label='Day of work',
                                          category=ROW_CATEGORY_SERVICE,
                                          quantity=10,
                                          unit_price='100',
                                          balance_payments=False,
                                          owner_id=1)

        i2 = Invoice.objects.create(customer_id=p.project.customer_id,
                                    invoice_id=2,
                                    state=INVOICE_STATE_EDITED,
                                    edition_date=datetime.date(2010, 8, 31),
                                    payment_date=datetime.date(2010, 9, 30),
                                    paid_date=None,
                                    payment_type=PAYMENT_TYPE_CHECK,
                                    execution_begin_date=datetime.date(2010, 8, 1),
                                    execution_end_date=datetime.date(2010, 8, 7),
                                    penalty_date=datetime.date(2010, 10, 8),
                                    penalty_rate='1.5',
                                    discount_conditions='Nothing',
                                    owner_id=1)

        i2_row = InvoiceRow.objects.create(proposal_id=p.id,
                                           invoice_id=i2.id,
                                           label='Day of work',
                                           category=ROW_CATEGORY_SERVICE,
                                           quantity=10,
                                           unit_price='100',
                                           balance_payments=True,
                                           owner_id=1)

        response = self.client.post(reverse('invoice_edit', kwargs={'id': i.id}),
                                    {'contact-name': i.customer.name,
                                     'address-street': '1 rue de la paix',
                                     'address-zipcode': '75001',
                                     'address-city': 'Paris',
                                     'invoice-invoice_id': 1,
                                     'invoice-state': INVOICE_STATE_EDITED,
                                     'invoice-edition_date': '2010-8-31',
                                     'invoice-payment_date': '2010-9-29',
                                     'invoice-paid_date': '2010-10-30',
                                     'invoice-payment_type': PAYMENT_TYPE_CHECK,
                                     'invoice-execution_begin_date': '2010-8-1',
                                     'invoice-execution_end_date': '2010-8-7',
                                     'invoice-penalty_date': '2010-10-8',
                                     'invoice-penalty_rate': 1.5,
                                     'invoice-discount_conditions':'Nothing',
                                     'invoice_rows-TOTAL_FORMS': 1,
                                     'invoice_rows-INITIAL_FORMS': 1,
                                     'invoice_rows-0-ownedobject_ptr': i_row.id,
                                     'invoice_rows-0-label': 'Day of work',
                                     'invoice_rows-0-proposal': p.id,
                                     'invoice_rows-0-category': ROW_CATEGORY_SERVICE,
                                     'invoice_rows-0-quantity': 10,
                                     'invoice_rows-0-unit_price': 100,
                                     'invoice_rows-0-balance_payments': False })

        self.assertEquals(response.status_code, 302)
        self.assertEquals(Invoice.objects.get(pk=i.id).payment_date, datetime.date(2010, 9, 29))

class ExpenseTest(TestCase):
    fixtures = ['test_users', ]

    def setUp(self):
        self.client.login(username='test', password='test')

    def testList(self):
        expense1 = Expense.objects.create(date=datetime.date(2010, 1, 1),
                                          reference='ABCD',
                                          amount='100.0',
                                          payment_type=PAYMENT_TYPE_CHECK,
                                          description='First expense',
                                          owner_id=1)
        expense2 = Expense.objects.create(date=datetime.date(2010, 2, 1),
                                          reference='BCDE',
                                          amount='200.0',
                                          payment_type=PAYMENT_TYPE_CASH,
                                          description='Second expense',
                                          owner_id=1)
        expense3 = Expense.objects.create(date=datetime.date(2010, 3, 1),
                                          reference='CDEF',
                                          amount='300.0',
                                          payment_type=PAYMENT_TYPE_CHECK,
                                          description='Third expense',
                                          owner_id=1)

        expenses = [expense1, expense2, expense3]

        response = self.client.get(reverse('expense_list'))
        expense_list = response.context['expenses'].object_list.all()
        self.assertEquals(set(expense_list), set(expenses))

    def testPostAdd(self):
        response = self.client.post(reverse('expense_add'),
                                    {'date': datetime.date(2010, 4, 1),
                                     'reference': 'DEFG',
                                     'supplier': 'Supplier 1',
                                     'amount': '400',
                                     'payment_type': PAYMENT_TYPE_CASH,
                                     'description': 'Add payment'})

        result = Expense.objects.filter(date=datetime.date(2010, 4, 1),
                                        reference='DEFG',
                                        supplier='Supplier 1',
                                        amount='400.0',
                                        payment_type=PAYMENT_TYPE_CASH,
                                        description='Add payment',
                                        owner__id=1)
        self.assertEqual(len(result), 1)
        json_response = simplejson.loads(response.content)
        self.assertEquals(json_response, {u'date': localize(datetime.date(2010, 4, 1)),
                                          u'reference': 'DEFG',
                                          u'supplier': 'Supplier 1',
                                          u'amount': '400',
                                          u'payment_type': PAYMENT_TYPE_CASH,
                                          u'payment_type_label': 'Cash',
                                          u'description': 'Add payment',
                                          u'id': result[0].id,
                                          u'error': 'ok'})

    def testPostEdit(self):
        expense1 = Expense.objects.create(date=datetime.date(2010, 1, 1),
                                          reference='ABCD',
                                          supplier='Supplier 1',
                                          amount='100.0',
                                          payment_type=PAYMENT_TYPE_CHECK,
                                          description='First expense',
                                          owner_id=1)
        response = self.client.post(reverse('expense_edit') + '?id=%d' % (expense1.id),
                                    {'date': datetime.date(2010, 4, 1),
                                     'reference': 'DEFG',
                                     'supplier': 'Supplier 1',
                                     'amount': '400',
                                     'payment_type': PAYMENT_TYPE_CASH,
                                     'description': 'Edit payment'})

        result = Expense.objects.filter(date=datetime.date(2010, 4, 1),
                                        reference='DEFG',
                                        supplier='Supplier 1',
                                        amount='400.0',
                                        payment_type=PAYMENT_TYPE_CASH,
                                        description='Edit payment',
                                        owner__id=1)
        self.assertEqual(len(result), 1)
        json_response = simplejson.loads(response.content)
        self.assertEquals(json_response, {u'date': localize(datetime.date(2010, 4, 1)),
                                          u'reference': 'DEFG',
                                          u'supplier': 'Supplier 1',
                                          u'amount': '400',
                                          u'payment_type': PAYMENT_TYPE_CASH,
                                          u'payment_type_label': 'Cash',
                                          u'description': 'Edit payment',
                                          u'id': expense1.id,
                                          u'error': 'ok'})

    def testPostDelete(self):
        expense1 = Expense.objects.create(date=datetime.date(2010, 1, 1),
                                          reference='ABCD',
                                          amount='100.0',
                                          payment_type=PAYMENT_TYPE_CHECK,
                                          description='First expense',
                                          owner_id=1)
        response = self.client.post(reverse('expense_delete'),
                                    {'id': expense1.id})

        result = Expense.objects.all()
        self.assertEqual(len(result), 0)
        json_response = simplejson.loads(response.content)
        self.assertEquals(json_response, {u'id': expense1.id,
                                          u'error': 'ok'})

    def testExpenseBookDownloadPdf(self):
        """
        Tests non-regression on pdf
        """
        for i in range(1, 50):
            expense = Expense.objects.create(date=datetime.date(2010, 1, 1),
                                             reference='ABCD',
                                             supplier='Supplier 1',
                                             amount='100.0',
                                             payment_type=PAYMENT_TYPE_CHECK,
                                             description='First expense',
                                             owner_id=1)


        response = self.client.get(reverse('expense_list_export') + '?year=%(year)s' % {'year': '2010'})
        self.assertEqual(response.status_code, 200)
        f = open('/tmp/expense_book.pdf', 'w')
        f.write(response.content)
        f.close()
        content = response.content.split("\n")
        invariant_content = content[0:85] + content[86:141] + content[142:-1]
        self.assertEquals(hashlib.md5("\n".join(invariant_content)).hexdigest(),
                          "a6fae2d556a9b261fd03e39316878e1b")
